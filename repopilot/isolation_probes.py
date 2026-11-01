"""Preserved Linux probe data and assertion checks. No executor or activation authority."""

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from importlib.resources import files
from typing import Literal

from pydantic import Field

from repopilot.policy import PolicyError, digest
from repopilot.worker_contract import Contract, ExecutionReceipt, VerificationJob

CATALOG_SHA256 = "c6d5f5acb91d0f57dd1de2918caaabd90cbb4d2788a57fb38c8964396e6f55a0"
ORIGIN_COMMIT = "37c01e9c6bb77b75940f4072aa8cf0974a8d8b37"
PROBE_NAMES = (
    "benign_checks_and_teardown",
    "filesystem_identity_network_and_secret_boundary",
    "disk_limit",
    "memory_limit",
    "process_limit",
    "cpu_deadline_and_cancellation",
)


@dataclass(frozen=True)
class Probe:
    name: str
    source: str
    source_sha256: str


def preserved_probes() -> tuple[Probe, ...]:
    raw = files("repopilot").joinpath("worker_probes.json").read_bytes()
    if len(raw) > 64000 or hashlib.sha256(raw).hexdigest() != CATALOG_SHA256:
        raise PolicyError("isolation_probe_catalog_changed")
    data = json.loads(raw)
    if data["origin_commit"] != ORIGIN_COMMIT:
        raise PolicyError("isolation_probe_origin_changed")
    probes = tuple(Probe(**row) for row in data["probes"])
    if tuple(p.name for p in probes) != PROBE_NAMES or any(
        hashlib.sha256(p.source.encode()).hexdigest() != p.source_sha256 for p in probes
    ):
        raise PolicyError("isolation_probe_payload_changed")
    return probes


def probe_job(name: str, phase: Literal["main", "cancel"] = "main") -> VerificationJob:
    probe = next((p for p in preserved_probes() if p.name == name), None)
    if (
        probe is None
        or phase not in {"main", "cancel"}
        or (phase == "cancel" and name != PROBE_NAMES[-1])
    ):
        raise PolicyError("isolation_probe_not_supported")
    stamp = int(time.time())
    deadline_probe = name == PROBE_NAMES[-1] and phase == "main"
    # These identify an explicitly synthetic security probe, never owner/model approval.
    return VerificationJob(
        run_id=uuid.uuid4().hex,
        nonce=uuid.uuid4().hex,
        baseline_sha="0" * 40,
        approval_digest="0" * 64,
        files={"test_boundary.py": probe.source},
        issued_at=stamp,
        expires_at=stamp + 300,
        memory_mib=128 if name == "memory_limit" else 512,
        timeout_seconds=5 if deadline_probe else 60,
        cpu_millis=250 if deadline_probe else 1000,
    )


class KernelObservation(Contract):
    """Expected observation shape, not a trustworthy self-attestation or signed receipt."""

    cpu_quota: int = Field(ge=1)
    cpu_period: int = Field(ge=1)
    memory_max: int = Field(ge=1)
    memory_swap_max: int = Field(ge=0)
    pids_max: int = Field(ge=1)
    throttled_before: int = Field(default=0, ge=0)
    throttled_after: int = Field(default=0, ge=0)
    oom_kills_before: int = Field(default=0, ge=0)
    oom_kills_after: int = Field(default=0, ge=0)

    def matches(self, job: VerificationJob) -> bool:
        return (
            self.cpu_quota * 1000 == self.cpu_period * job.cpu_millis
            and self.memory_max == job.memory_mib * 1048576
            and self.memory_swap_max == 0
            and self.pids_max == job.process_limit
        )


class ProbeObservation(Contract):
    guest_process_started: bool = False
    guest_uid: int = Field(default=-1, ge=-1)
    kernel: KernelObservation | None = None
    host_network_adapters: int | None = Field(default=None, ge=0)
    host_directory_shares: int | None = Field(default=None, ge=0)
    readonly_guest_root: bool = False
    cleanup_confirmed: bool = False
    remaining_guest_processes: int | None = Field(default=None, ge=0)
    cancellation_after_guest_start: bool = False


@dataclass(frozen=True)
class ProbeAssertion:
    assertions_satisfied: bool
    reason: str
    # Even positive synthetic inputs cannot authorize the production worker.
    activation_authorized: bool = False


def assess_probe(
    name: str,
    job: VerificationJob,
    receipt: ExecutionReceipt,
    observed: ProbeObservation,
    phase: Literal["main", "cancel"] = "main",
) -> ProbeAssertion:
    job = VerificationJob.model_validate(job.model_dump())
    receipt = ExecutionReceipt.model_validate(receipt.model_dump())
    observed = ProbeObservation.model_validate(observed.model_dump())
    expected = probe_job(name, phase)
    if any(
        getattr(job, key) != getattr(expected, key)
        for key in (
            "files",
            "profile",
            "uid",
            "network",
            "memory_mib",
            "disk_mib",
            "timeout_seconds",
            "cpu_millis",
            "process_limit",
            "baseline_sha",
            "approval_digest",
        )
    ):
        return ProbeAssertion(False, "probe_payload_or_limits_changed")
    if (
        receipt.run_id != job.run_id
        or receipt.nonce != job.nonce
        or receipt.job_digest != digest(job.model_dump())
    ):
        return ProbeAssertion(False, "receipt_identity_mismatch")
    if not observed.guest_process_started:
        return ProbeAssertion(False, "guest_execution_not_observed")
    if (
        observed.guest_uid != 65532
        or observed.host_network_adapters != 0
        or observed.host_directory_shares != 0
        or not observed.readonly_guest_root
        or observed.kernel is None
        or not observed.kernel.matches(job)
    ):
        return ProbeAssertion(False, "effective_boundary_or_limits_unconfirmed")
    if not observed.cleanup_confirmed or observed.remaining_guest_processes != 0:
        return ProbeAssertion(False, "cleanup_unconfirmed")
    if phase == "cancel":
        passed = receipt.outcome == "cancelled" and observed.cancellation_after_guest_start
    elif name == "benign_checks_and_teardown":
        passed = receipt.outcome == "completed" and all(
            c.exit_code == 0 and not c.timed_out and not c.cancelled for c in receipt.checks
        )
    else:
        first = receipt.checks[0] if receipt.checks else None
        passed = False
        if first and first.name == "pytest":
            if name == "memory_limit":
                passed = (
                    receipt.outcome == "failed"
                    and not first.timed_out
                    and not first.cancelled
                    and (
                        (
                            first.exit_code == 137
                            and observed.kernel.oom_kills_after > observed.kernel.oom_kills_before
                        )
                        or (first.exit_code != 0 and "MemoryError" in first.output)
                    )
                )
            elif name == "cpu_deadline_and_cancellation":
                passed = (
                    receipt.outcome == "failed"
                    and first.timed_out
                    and not first.cancelled
                    and observed.kernel.throttled_after > observed.kernel.throttled_before
                )
            else:
                passed = first.exit_code == 0 and not first.timed_out and not first.cancelled
    return ProbeAssertion(
        bool(passed), "assertions_satisfied" if passed else "probe_assertion_failed"
    )
