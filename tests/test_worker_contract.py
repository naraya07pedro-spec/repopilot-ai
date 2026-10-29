"""Worker protocol tests only; no sandbox or repository code is executed."""

import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_owner import REPO, service

from repopilot.policy import PolicyError, digest
from repopilot.worker_contract import (
    COMMANDS,
    DisabledWorker,
    Envelope,
    ExecutionReceipt,
    VerificationJob,
    WorkerCheck,
    WorkerLedger,
    authenticate,
    sign,
    validate_job,
)

KEY = b"test-only-worker-controller-key-32-bytes"


def job(**changes):
    stamp = int(time.time())
    return VerificationJob(
        run_id="a" * 32,
        nonce="b" * 32,
        baseline_sha="c" * 40,
        approval_digest="d" * 64,
        files={"app.py": "pass\n"},
        issued_at=stamp,
        expires_at=stamp + 60,
        **changes,
    )


def setup(store):
    s = service(store)
    row, _ = s.create(REPO, 1, "worker-contract", paid_approved=True)
    s.prepare(row["id"])
    data = s.get(row["id"])
    s.approve(row["id"], data["approval_digest"])
    return s, WorkerLedger(s, KEY), row["id"]


def receipt(order, outcome="completed", code=0):
    payload = ExecutionReceipt(
        run_id=order.run_id,
        nonce=order.nonce,
        job_digest=digest(order.model_dump()),
        outcome=outcome,
        checks=[
            WorkerCheck(
                name=n,
                command=c,
                exit_code=code,
                output="contract fixture only",
                duration_seconds=0.1,
            )
            for n, c in COMMANDS.items()
        ]
        if outcome != "cancelled"
        else [],
    )
    return sign(payload.model_dump(), KEY, "receipt")


def test_authentication_domains_and_tampering():
    original = job()
    signed = sign(original.model_dump(), KEY, "job")
    assert validate_job(signed, KEY) == original
    with pytest.raises(PolicyError, match="authentication"):
        authenticate(signed, KEY, "receipt")
    with pytest.raises(PolicyError, match="authentication"):
        validate_job(signed, b"another-controller-key-" * 2)
    altered = Envelope(payload={**signed.payload, "uid": 0}, signature=signed.signature)
    with pytest.raises(PolicyError, match="authentication"):
        validate_job(altered, KEY)
    with pytest.raises(PolicyError, match="too_short"):
        sign({}, b"short", "job")
    with pytest.raises(PolicyError, match="message_limit"):
        sign({"data": "x" * 256001}, KEY, "job")


@pytest.mark.parametrize(
    "path",
    [
        "../app.py",
        "/app.py",
        ".github/task.py",
        "a//app.py",
        "a/../app.py",
        "a\\app.py",
        "a.py:stream",
        "NUL.py",
        "requirements.txt",
    ],
)
def test_unsafe_source_paths_rejected(path):
    data = job().model_dump()
    data["files"] = {path: "pass"}
    with pytest.raises(ValueError, match="worker_source_policy"):
        VerificationJob.model_validate(data)


@pytest.mark.parametrize(
    "changes",
    [
        {"memory_mib": 513},
        {"disk_mib": 65},
        {"cpu_millis": 1001},
        {"process_limit": 33},
        {"timeout_seconds": 61},
        {"network": "allow"},
        {"uid": 0},
        {"environment": {"API_KEY": "not-allowed"}},
        {"shell": "sh -c unsafe"},
        {"files": {"app.py": "x" * 128001}},
    ],
)
def test_resource_and_input_policy(changes):
    with pytest.raises(ValueError):
        VerificationJob.model_validate({**job().model_dump(), **changes})


def test_expired_job_is_not_claimed():
    data = job().model_dump()
    data.update(issued_at=1, expires_at=100)
    with pytest.raises(PolicyError, match="expired"):
        validate_job(sign(data, KEY, "job"), KEY)
    with pytest.raises(ValueError, match="lease_limit"):
        VerificationJob.model_validate({**data, "expires_at": 1000})


def test_idempotent_job_atomic_claim_and_receipt_replay(store):
    s, ledger, identity = setup(store)
    envelope = ledger.prepare(identity)
    assert ledger.prepare(identity) == envelope

    def claim(_):
        try:
            return ledger.claim(envelope)
        except PolicyError:
            return None

    with ThreadPoolExecutor(max_workers=4) as pool:
        accepted = [r for r in pool.map(claim, range(4)) if r is not None]
    assert len(accepted) == 1
    report = receipt(accepted[0])
    complete = ledger.accept(report)
    assert complete["status"] == "verification_passed"
    assert complete["status"] != "completed" and "pr" not in complete
    assert ledger.accept(report) == complete
    assert s.get(identity)["worker_receipt"]["checks"][0]["exit_code"] == 0
    with pytest.raises(PolicyError, match="state_conflict"):
        ledger.accept(receipt(accepted[0], code=1))


@pytest.mark.parametrize("cancel_before_claim", [True, False])
def test_cancel_requires_worker_acknowledgement(store, cancel_before_claim):
    s, ledger, identity = setup(store)
    envelope = ledger.prepare(identity)
    order = validate_job(envelope, KEY)
    if not cancel_before_claim:
        ledger.claim(envelope)
    assert ledger.cancel(identity)["status"] == "cancel_requested"
    assert ledger.cancel(identity)["status"] == "cancel_requested"
    if cancel_before_claim:
        with pytest.raises(PolicyError, match="state_conflict"):
            ledger.claim(envelope)
    with pytest.raises(PolicyError, match="cancel_pending"):
        ledger.accept(receipt(order))
    assert ledger.accept(receipt(order, outcome="cancelled"))["status"] == "cancelled"
    assert s.get(identity)["events"][-1]["name"] == "cancelled"


def test_interruption_never_replays_or_accepts_late_success(store):
    s, ledger, identity = setup(store)
    order = ledger.claim(ledger.prepare(identity))
    ledger.recover()
    recovered = WorkerLedger(s, KEY)
    assert s.get(identity)["status"] == "interrupted"
    assert s.get(identity)["events"][-1]["name"] == "interrupted"
    with pytest.raises(PolicyError, match="state_conflict"):
        recovered.accept(receipt(order))
    with pytest.raises(PolicyError, match="approval_required"):
        recovered.prepare(identity)


def test_failed_tests_remain_failed(store):
    s, ledger, identity = setup(store)
    order = ledger.claim(ledger.prepare(identity))
    failed = ledger.accept(receipt(order, code=1))
    assert failed["status"] == "verification_failed"
    assert s.get(identity)["worker_receipt"]["checks"][0]["exit_code"] == 1


def test_receipt_evidence_cannot_invent_checks_or_commands():
    base = receipt(job()).payload
    with pytest.raises(ValueError, match="checks_missing"):
        ExecutionReceipt.model_validate({**base, "checks": []})
    with pytest.raises(ValueError, match="duplicate_check"):
        ExecutionReceipt.model_validate({**base, "checks": [base["checks"][0]] * 2})
    for changed in [
        {"command": ["sh", "-c", "unsafe"]},
        {"output": "x" * 16001},
        {"duration_seconds": float("nan")},
    ]:
        with pytest.raises(ValueError):
            WorkerCheck.model_validate({**base["checks"][0], **changed})


def test_receipt_mismatch_expiry_and_reported_time_limit(store):
    s, ledger, identity = setup(store)
    order = ledger.claim(ledger.prepare(identity))
    report = receipt(order)
    with pytest.raises(PolicyError, match="receipt_mismatch"):
        ledger.accept(sign({**report.payload, "nonce": "f" * 32}, KEY, "receipt"))
    checks = [{**c, "duration_seconds": 30.0} for c in report.payload["checks"]]
    with pytest.raises(PolicyError, match="time_limit"):
        ledger.accept(sign({**report.payload, "checks": checks}, KEY, "receipt"))
    data = s.get(identity)
    data["worker_job"]["expires_at"] = 1
    s.transition(identity, ["executing"], "executing", data)
    updated = {**report.payload, "job_digest": digest(data["worker_job"])}
    with pytest.raises(PolicyError, match="lease_expired"):
        ledger.accept(sign(updated, KEY, "receipt"))


def test_approval_configuration_and_job_binding(store):
    s, ledger, identity = setup(store)
    data = s.get(identity)
    data["approval_expires"] = 0
    s.transition(identity, ["approved"], "approved", data)
    with pytest.raises(PolicyError, match="approval_invalid"):
        ledger.prepare(identity)
    with pytest.raises(PolicyError, match="too_short"):
        WorkerLedger(s, b"short")
    with pytest.raises(PolicyError, match="isolated_worker_unavailable"):
        DisabledWorker().require_available()
    assert not DisabledWorker.available


def test_job_secret_and_receipt_secret_rejected():
    value = "sk-" + "a" * 30
    with pytest.raises(ValueError, match="source_policy"):
        VerificationJob.model_validate({**job().model_dump(), "files": {"app.py": value}})
    with pytest.raises(ValueError, match="check_policy"):
        WorkerCheck(
            name="pytest",
            command=COMMANDS["pytest"],
            exit_code=0,
            output=value,
            duration_seconds=0.1,
        )


def test_recovery_includes_jobs_older_than_history_page(store):
    s = service(store)
    identities = []
    for index in range(101):
        row, _ = s.create(REPO, 1, f"old-worker-{index}", paid_approved=True)
        s.transition(row["id"], ["queued"], "worker_queued")
        identities.append(row["id"])
    assert len(s.history()) == 100
    WorkerLedger(s, KEY).recover()
    assert all(s.get(identity)["status"] == "interrupted" for identity in identities)


def test_cancellation_race_cannot_be_overwritten_by_receipt(store, monkeypatch):
    s, ledger, identity = setup(store)
    order = ledger.claim(ledger.prepare(identity))
    original = s.transition

    def racing(run_id, before, after, payload=None):
        if after == "verification_passed":
            ledger.cancel(run_id)
        return original(run_id, before, after, payload)

    monkeypatch.setattr(s, "transition", racing)
    with pytest.raises(PolicyError, match="state_conflict"):
        ledger.accept(receipt(order))
    assert s.get(identity)["status"] == "cancel_requested"
    assert "worker_receipt" not in s.get(identity)
