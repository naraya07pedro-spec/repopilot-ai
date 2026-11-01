"""Assertion-contract tests only. No guest, sandbox or stress payload is executed."""

import hashlib
import subprocess

import pytest

import repopilot.isolation_probes as probe_module
from repopilot.isolation_probes import (
    PROBE_NAMES,
    KernelObservation,
    ProbeObservation,
    assess_probe,
    preserved_probes,
    probe_job,
)
from repopilot.policy import PolicyError, digest
from repopilot.worker_contract import COMMANDS, DisabledWorker, ExecutionReceipt, WorkerCheck


def observation(job, **changes):
    return ProbeObservation(
        **{
            "guest_process_started": True,
            "guest_uid": 65532,
            "kernel": KernelObservation(
                cpu_quota=job.cpu_millis * 100,
                cpu_period=100000,
                memory_max=job.memory_mib * 1048576,
                memory_swap_max=0,
                pids_max=job.process_limit,
                throttled_after=1,
                oom_kills_after=1,
            ),
            "host_network_adapters": 0,
            "host_directory_shares": 0,
            "readonly_guest_root": True,
            "cleanup_confirmed": True,
            "remaining_guest_processes": 0,
            "cancellation_after_guest_start": True,
            **changes,
        }
    )


def receipt(job, *, outcome="completed", code=0, timed_out=False):
    return ExecutionReceipt(
        run_id=job.run_id,
        nonce=job.nonce,
        job_digest=digest(job.model_dump()),
        outcome=outcome,
        checks=[
            WorkerCheck(
                name=name,
                command=command,
                exit_code=code,
                output="synthetic assertion fixture; no guest ran",
                duration_seconds=0.1,
                timed_out=timed_out,
            )
            for name, command in COMMANDS.items()
        ]
        if outcome == "completed"
        else []
        if outcome == "cancelled"
        else [
            WorkerCheck(
                name="pytest",
                command=COMMANDS["pytest"],
                exit_code=code,
                output="synthetic assertion fixture",
                duration_seconds=0.1,
                timed_out=timed_out,
            )
        ],
    )


def test_preserved_payloads_and_job_creation_launch_nothing(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Probe preparation must not start a process")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    probes = preserved_probes()
    assert len(probes) == 6 and tuple(p.name for p in probes) == PROBE_NAMES
    assert all(hashlib.sha256(p.source.encode()).hexdigest() == p.source_sha256 for p in probes)
    for p in probes:
        job = probe_job(p.name)
        assert job.files == {"test_boundary.py": p.source}
        assert job.uid == 65532 and job.network == "deny" and job.disk_mib == 64
    assert probe_job("memory_limit").memory_mib == 128
    deadline = probe_job(PROBE_NAMES[-1])
    assert deadline.cpu_millis == 250 and deadline.timeout_seconds == 5
    cancel = probe_job(PROBE_NAMES[-1], "cancel")
    assert cancel.cpu_millis == 1000 and cancel.timeout_seconds == 60


def test_modified_packaged_probe_catalog_is_rejected(tmp_path, monkeypatch):
    (tmp_path / "worker_probes.json").write_text('{"probes": []}', encoding="utf-8")
    monkeypatch.setattr(probe_module, "files", lambda _: tmp_path)
    with pytest.raises(PolicyError, match="catalog_changed"):
        preserved_probes()


@pytest.mark.parametrize("name", PROBE_NAMES)
def test_synthetic_positive_assertions_never_authorize_a_worker(name):
    job = probe_job(name)
    result = (
        receipt(job, outcome="failed", code=137)
        if name == "memory_limit"
        else receipt(job, outcome="failed", code=1, timed_out=True)
        if name == PROBE_NAMES[-1]
        else receipt(job)
    )
    verdict = assess_probe(name, job, result, observation(job))
    assert verdict.assertions_satisfied and not verdict.activation_authorized
    assert not DisabledWorker().available


@pytest.mark.parametrize(
    "changed",
    [
        {"guest_process_started": False},
        {"guest_uid": 0},
        {"kernel": None},
        {"host_network_adapters": None},
        {"host_network_adapters": 1},
        {"host_directory_shares": 1},
        {"readonly_guest_root": False},
        {"cleanup_confirmed": False},
        {"remaining_guest_processes": None},
        {"remaining_guest_processes": 1},
    ],
)
def test_missing_boundaries_or_cleanup_fail_before_a_zero_exit_can_pass(changed):
    job = probe_job(PROBE_NAMES[0])
    assert not assess_probe(
        PROBE_NAMES[0], job, receipt(job), observation(job, **changed)
    ).assertions_satisfied


def test_startup_failure_and_deadline_kill_are_not_memory_enforcement():
    name = "memory_limit"
    job = probe_job(name)
    assert not assess_probe(
        name,
        job,
        receipt(job, outcome="failed", code=137),
        observation(job, guest_process_started=False),
    ).assertions_satisfied
    assert not assess_probe(
        name, job, receipt(job, outcome="failed", code=137, timed_out=True), observation(job)
    ).assertions_satisfied
    observed = observation(job)
    observed = observed.model_copy(
        update={"kernel": observed.kernel.model_copy(update={"oom_kills_after": 0})}
    )
    assert not assess_probe(
        name, job, receipt(job, outcome="failed", code=137), observed
    ).assertions_satisfied


def test_cpu_requires_real_throttling_delta_and_exact_kernel_limits():
    name = PROBE_NAMES[-1]
    job = probe_job(name)
    result = receipt(job, outcome="failed", code=1, timed_out=True)
    for changed in ({"throttled_after": 0}, {"cpu_quota": 100000}, {"memory_swap_max": 1}):
        observed = observation(job)
        observed = observed.model_copy(
            update={"kernel": observed.kernel.model_copy(update=changed)}
        )
        assert not assess_probe(name, job, result, observed).assertions_satisfied


def test_cancellation_requires_running_guest_and_matching_receipt():
    name = PROBE_NAMES[-1]
    job = probe_job(name, "cancel")
    result = receipt(job, outcome="cancelled")
    assert assess_probe(name, job, result, observation(job), "cancel").assertions_satisfied
    assert not assess_probe(
        name, job, result, observation(job, cancellation_after_guest_start=False), "cancel"
    ).assertions_satisfied
    forged = result.model_copy(update={"nonce": "f" * 32})
    assert not assess_probe(name, job, forged, observation(job), "cancel").assertions_satisfied


def test_edited_probe_limits_and_unsupported_names_fail_closed():
    job = probe_job("disk_limit")
    changed = job.model_copy(update={"disk_mib": 8})
    assert not assess_probe(
        "disk_limit", changed, receipt(changed), observation(changed)
    ).assertions_satisfied
    with pytest.raises(PolicyError, match="not_supported"):
        probe_job("unknown")
    with pytest.raises(PolicyError, match="not_supported"):
        probe_job("disk_limit", "cancel")
