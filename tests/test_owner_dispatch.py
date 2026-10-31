"""Owner scheduling contract only: synthetic receipts, never candidate execution."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from test_worker_contract import KEY, receipt, setup

from repopilot.owner_dispatch import OwnerDispatcher
from repopilot.policy import PolicyError
from repopilot.worker_contract import Envelope, authenticate, validate_job
from repopilot.worker_dispatch import WorkerDispatcher, WorkerTransport, candidate_files


class PendingPool:
    def __init__(self, fail=False):
        self.pending = []
        self.fail = fail

    def submit(self, function, *args):
        if self.fail:
            raise RuntimeError("pool closed")
        self.pending.append((function, args))

    def finish(self):
        function, args = self.pending.pop()
        function(*args)


def dispatcher(store, tmp_path, pool=None):
    service, _, identity = setup(store)
    calls = []

    def handler(request):
        calls.append(request)
        order = validate_job(Envelope.model_validate(json.loads(request.content)), KEY)
        with candidate_files(order, tmp_path) as root:
            assert (root / "app.py").read_bytes() == order.files["app.py"].encode()
        return httpx.Response(200, json=receipt(order).model_dump())

    worker = WorkerDispatcher(
        service,
        KEY,
        WorkerTransport(
            "http://127.0.0.1:8012",
            KEY,
            httpx.Client(transport=httpx.MockTransport(handler), trust_env=False),
        ),
        lambda: None,  # Contract-test injection; this does not establish isolation.
    )
    slots = threading.BoundedSemaphore(1)
    return OwnerDispatcher(service, pool or PendingPool(), slots, worker), calls, identity


def test_default_gate_precedes_job_creation_and_capacity(store, tmp_path):
    scheduled, calls, identity = dispatcher(store, tmp_path)
    disabled = OwnerDispatcher(scheduled.service, scheduled.pool, scheduled.slots)
    with pytest.raises(PolicyError, match="isolated_worker_unavailable"):
        disabled.execute(identity)
    assert disabled.service.get(identity)["status"] == "approved"
    assert not scheduled.pool.pending and not calls
    assert scheduled.slots.acquire(blocking=False)


def test_concurrent_duplicate_execute_submits_one_candidate(store, tmp_path):
    scheduled, calls, identity = dispatcher(store, tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        states = list(pool.map(lambda _: scheduled.execute(identity)["status"], range(4)))
    assert states == ["worker_queued"] * 4
    assert len(scheduled.pool.pending) == 1 and not calls
    scheduled.pool.finish()
    assert len(calls) == 1
    assert scheduled.service.get(identity)["status"] == "verification_passed"
    assert not list(tmp_path.glob("candidate-*"))
    assert scheduled.slots.acquire(blocking=False)


def test_queued_cancel_wins_without_sending_candidate(store, tmp_path):
    scheduled, calls, identity = dispatcher(store, tmp_path)
    scheduled.execute(identity)
    assert scheduled.cancel(identity)["status"] == "cancelled"
    scheduled.pool.finish()
    assert not calls
    assert scheduled.service.get(identity)["status"] == "cancelled"
    assert scheduled.slots.acquire(blocking=False)


def test_model_change_and_capacity_preserve_approval_and_slots(store, tmp_path):
    scheduled, calls, identity = dispatcher(store, tmp_path)
    scheduled.slots.acquire()
    with pytest.raises(PolicyError, match="capacity"):
        scheduled.execute(identity)
    scheduled.slots.release()
    scheduled.service.planner.profile = scheduled.service.planner.profile.model_copy(
        update={"request_timeout_seconds": 120}
    )
    with pytest.raises(PolicyError, match="model_configuration_changed"):
        scheduled.execute(identity)
    assert scheduled.service.get(identity)["status"] == "approved"
    assert scheduled.slots.acquire(blocking=False)
    assert not calls and not scheduled.pool.pending


def test_failed_submission_persists_interruption_without_replay(store, tmp_path):
    scheduled, calls, identity = dispatcher(store, tmp_path, PendingPool(fail=True))
    with pytest.raises(PolicyError, match="not_submitted"):
        scheduled.execute(identity)
    assert scheduled.service.get(identity)["status"] == "interrupted"
    with pytest.raises(PolicyError, match="approval_required"):
        scheduled.execute(identity)
    assert scheduled.slots.acquire(blocking=False)
    assert not calls


def test_restart_does_not_replay_queued_execution(store, tmp_path):
    scheduled, calls, identity = dispatcher(store, tmp_path)
    scheduled.execute(identity)
    scheduled.service.recover()
    scheduled.pool.finish()
    assert scheduled.service.get(identity)["status"] == "interrupted"
    assert not calls
    assert scheduled.slots.acquire(blocking=False)


@pytest.mark.parametrize("uncertain", [False, True])
def test_active_cancel_requires_receipt_and_unknown_cancel_is_not_replayed(
    store, tmp_path, uncertain
):
    scheduled, _, identity = dispatcher(store, tmp_path)
    scheduled.execute(identity)
    order = scheduled.worker.ledger.claim(scheduled.worker.ledger.prepare(identity))
    calls = []

    def handler(request):
        assert request.url.path == "/v1/cancel"
        authenticate(Envelope.model_validate(json.loads(request.content)), KEY, "cancel")
        calls.append(request)
        if uncertain:
            raise httpx.ReadTimeout("synthetic lost cancellation acknowledgement")
        return httpx.Response(200, json=receipt(order, outcome="cancelled").model_dump())

    scheduled.worker.transport.client = httpx.Client(
        transport=httpx.MockTransport(handler), trust_env=False
    )
    if uncertain:
        with pytest.raises(PolicyError, match="transport_unknown"):
            scheduled.cancel(identity)
        assert scheduled.cancel(identity)["status"] == "cancel_requested"
    else:
        assert scheduled.cancel(identity)["status"] == "cancelled"
    assert len(calls) == 1
    scheduled.pool.finish()
    assert scheduled.service.get(identity)["status"] == (
        "cancel_requested" if uncertain else "cancelled"
    )
    assert scheduled.slots.acquire(blocking=False)
