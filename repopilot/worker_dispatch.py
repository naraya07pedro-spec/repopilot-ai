"""Worker HTTP integration. No runtime enable switch and no host code executor."""

import json
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

import httpx

from repopilot.policy import PolicyError, digest, safe_path
from repopilot.private_service import PrivateService
from repopilot.store import now
from repopilot.worker_contract import (
    DisabledWorker,
    Envelope,
    VerificationJob,
    WorkerLedger,
    authenticate,
    sign,
)
from repopilot.workspace import assert_snapshot


@contextmanager
def candidate_files(job: VerificationJob, parent: Path) -> Iterator[Path]:
    """Materialize authenticated text only; never import it or run repository commands."""
    job = VerificationJob.model_validate(job.model_dump())
    with tempfile.TemporaryDirectory(prefix="candidate-", dir=parent) as folder:
        root = Path(folder)
        for name, content in job.files.items():
            path = safe_path(root, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="")
        assert_snapshot(root, job.files)
        yield root
        assert_snapshot(root, job.files)


class WorkerTransport:
    def __init__(self, endpoint: str, key: bytes, client: httpx.Client):
        url = urlparse(endpoint)
        if (
            url.scheme != "http"
            or url.hostname not in {"127.0.0.1", "::1"}
            or not url.port
            or url.username
            or url.password
            or url.path not in {"", "/"}
            or url.query
            or url.fragment
            or len(key) < 32
        ):
            raise PolicyError("worker_transport_configuration")
        self.endpoint, self._key, self.client = endpoint.rstrip("/"), key, client

    def call(self, operation: str, envelope: Envelope) -> Envelope:
        if operation not in {"execute", "cancel"}:
            raise PolicyError("worker_operation_not_allowed")
        authenticate(envelope, self._key, "job" if operation == "execute" else "cancel")
        try:
            with self.client.stream(
                "POST",
                self.endpoint + "/v1/" + operation,
                json=envelope.model_dump(),
                timeout=120,
                follow_redirects=False,
            ) as response:
                if response.status_code != 200:
                    raise PolicyError(f"worker_http_{response.status_code}")
                content = bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > 256000:
                        raise PolicyError("worker_response_limit")
                result = Envelope.model_validate(json.loads(content))
                authenticate(result, self._key, "receipt")
                return result
        except httpx.HTTPError:
            # A lost response is not permission to repeat an execution request.
            raise PolicyError("worker_transport_unknown") from None
        except PolicyError:
            raise
        except (ValueError, TypeError):
            raise PolicyError("worker_response_invalid") from None


class WorkerDispatcher:
    def __init__(
        self,
        service: PrivateService,
        key: bytes,
        transport: WorkerTransport,
        require_runtime: Callable[[], None] | None = None,
    ):
        self.service, self._key, self.transport = service, key, transport
        self.ledger = WorkerLedger(service, key)
        self.require_runtime = require_runtime or DisabledWorker().require_available

    def execute(self, identity: str) -> None:
        self.require_runtime()
        envelope = self.ledger.prepare(identity)
        self.ledger.claim(envelope)
        try:
            result = self.transport.call("execute", envelope)
            self.ledger.accept(result)
        except Exception:
            data = self.service.get(identity)
            data["failure_category"] = "worker_dispatch_uncertain"
            data["events"].append({"at": now(), "name": "interrupted"})
            self.service.transition(
                identity, ["executing", "cancel_requested"], "interrupted", data
            )
            raise PolicyError("worker_dispatch_uncertain: reconcile before retry") from None

    def cancel(self, identity: str) -> None:
        self.require_runtime()
        data = self.ledger.cancel(identity)
        if data["status"] != "cancel_requested":
            return
        job = data["worker_job"]
        message = sign(
            {
                "run_id": identity,
                "nonce": job["nonce"],
                "job_digest": digest(job),
                "expires_at": job["expires_at"],
            },
            self._key,
            "cancel",
        )
        self.ledger.accept(self.transport.call("cancel", message))
