"""Owner scheduling behind the unavailable worker gate; never executes candidate code."""

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from repopilot.policy import PolicyError
from repopilot.private_service import PrivateService
from repopilot.store import now
from repopilot.worker_contract import DisabledWorker
from repopilot.worker_dispatch import WorkerDispatcher


class OwnerDispatcher:
    """One application process, durable job claim, bounded shared scheduling capacity.

    Production supplies no worker. Explicit dependency injection is for contract tests and
    future reviewed composition, not an environment-variable activation mechanism.
    """

    def __init__(
        self,
        service: PrivateService,
        pool: ThreadPoolExecutor,
        slots: threading.BoundedSemaphore,
        worker: WorkerDispatcher | None = None,
    ):
        self.service, self.pool, self.slots, self.worker = service, pool, slots, worker
        self.lock = threading.Lock()

    def require_worker(self) -> WorkerDispatcher:
        if self.worker is None:
            DisabledWorker().require_available()
            raise AssertionError("unreachable")
        self.worker.require_runtime()
        return self.worker

    def interrupted(self, identity: str) -> None:
        data = self.service.get(identity)
        if data["status"] == "worker_queued":
            data["failure_category"] = "owner_dispatch_interrupted"
            data["events"].append({"at": now(), "name": "interrupted"})
            self.service.transition(identity, ["worker_queued"], "interrupted", data)

    def work(self, worker: WorkerDispatcher, identity: str) -> None:
        try:
            worker.execute(identity)
        except Exception:
            # The transport dispatcher owns uncertain in-flight results. Only an unclaimed
            # queued job can be interrupted here; never erase a receipt/cancellation.
            self.interrupted(identity)
        finally:
            self.slots.release()

    def execute(self, identity: str) -> dict[str, Any]:
        worker = self.require_worker()  # Must precede job creation, pool use and transport.
        with self.lock:
            data = self.service.get(identity)
            if data["status"] in {"worker_queued", "executing", "cancel_requested"}:
                return data  # A duplicate request never submits another execution.
            if data["status"] != "approved":
                raise PolicyError("worker_approval_required")
            if not self.slots.acquire(blocking=False):
                raise PolicyError("owner_execution_capacity")
            try:
                worker.ledger.prepare(identity)  # Recheck scope, model, lease and exact files.
            except Exception:
                self.slots.release()
                raise
            try:
                self.pool.submit(self.work, worker, identity)
            except Exception:
                self.interrupted(identity)
                self.slots.release()
                raise PolicyError("owner_dispatch_not_submitted") from None
        return self.service.get(identity)

    def cancel(self, identity: str) -> dict[str, Any]:
        with self.lock:
            data = self.service.get(identity)
            if data["status"] == "worker_queued":
                self.require_worker()
                data["events"].append({"at": now(), "name": "cancelled"})
                # CAS against the worker claim: if cancellation wins, no request is sent.
                if self.service.transition(identity, ["worker_queued"], "cancelled", data):
                    return self.service.get(identity)
                data = self.service.get(identity)
            if data["status"] == "executing":
                self.require_worker().cancel(identity)
                return self.service.get(identity)
            if data["status"] == "cancel_requested":
                return data  # Await acknowledgement; do not replay cancellation automatically.
            return self.service.stop(identity, "cancelled")
