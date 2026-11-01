"""Admission and qualification planning only. No VM API, process or code executor.

Positive synthetic inputs never authorize VM operations or activate a worker. The
Windows lifecycle script independently retains its unconditional code-only guard.
"""

from typing import Literal

from pydantic import Field

from repopilot.isolation_probes import preserved_probes, probe_job
from repopilot.worker_contract import Contract

MIB = 1048576


class AdmissionPolicy(Contract):
    start_available_mib: Literal[2048] = 2048
    start_commit_headroom_mib: Literal[2048] = 2048
    start_commit_percent_max: Literal[85] = 85
    start_cpu_percent_max: Literal[80] = 80
    system_disk_free_mib_min: Literal[4096] = 4096
    worker_disk_free_mib_min: Literal[4096] = 4096
    sample_window_seconds: Literal[30] = 30
    sample_gap_seconds_max: Literal[3] = 3
    running_available_mib_min: Literal[768] = 768
    running_commit_percent_max: Literal[90] = 90
    running_cpu_percent_max: Literal[95] = 95
    sustained_pressure_seconds: Literal[5] = 5
    critical_available_mib: Literal[512] = 512
    watchdog_sample_seconds: Literal[1] = 1
    watchdog_heartbeat_timeout_seconds: Literal[3] = 3
    owned_vm_lifetime_seconds_max: Literal[600] = 600


class HostSample(Contract):
    sampled_at: float = Field(ge=0, allow_inf_nan=False)
    available_bytes: int = Field(ge=0)
    commit_headroom_bytes: int = Field(ge=0)
    commit_percent: float = Field(ge=0, le=100, allow_inf_nan=False)
    cpu_percent: float = Field(ge=0, le=100, allow_inf_nan=False)
    system_disk_free_bytes: int = Field(ge=0)
    worker_disk_free_bytes: int = Field(ge=0)
    model_runtime_absent: bool | None = None


class AdmissionDecision(Contract):
    resource_checks_passed: bool
    reasons: tuple[str, ...]
    vm_operations_authorized: Literal[False] = False
    production_execution_enabled: Literal[False] = False


def admission(samples: list[HostSample], now: float) -> AdmissionDecision:
    """Demand a fresh, sustained window. Unknown facts or pressures deny admission."""
    policy = AdmissionPolicy()
    reasons = []
    if (
        len(samples) < 11
        or samples[-1].sampled_at - samples[0].sampled_at < policy.sample_window_seconds
        or samples[-1].sampled_at - samples[0].sampled_at > 40
        or not 0 <= now - samples[-1].sampled_at <= policy.sample_gap_seconds_max
        or any(
            not 0 < b.sampled_at - a.sampled_at <= policy.sample_gap_seconds_max
            for a, b in zip(samples, samples[1:], strict=False)
        )
    ):
        reasons.append("fresh_contiguous_30_second_window_required")
    if any(s.available_bytes < policy.start_available_mib * MIB for s in samples):
        reasons.append("available_ram_below_2048_MiB")
    if any(
        s.commit_headroom_bytes < policy.start_commit_headroom_mib * MIB
        or s.commit_percent > policy.start_commit_percent_max
        for s in samples
    ):
        reasons.append("commit_headroom_or_load_failed")
    if any(s.cpu_percent > policy.start_cpu_percent_max for s in samples):
        reasons.append("host_cpu_above_80_percent")
    if any(
        s.system_disk_free_bytes < policy.system_disk_free_mib_min * MIB
        or s.worker_disk_free_bytes < policy.worker_disk_free_mib_min * MIB
        for s in samples
    ):
        reasons.append("C_or_D_free_space_below_4096_MiB")
    if not samples or any(s.model_runtime_absent is not True for s in samples):
        reasons.append("model_runtime_absence_unconfirmed")
    return AdmissionDecision(resource_checks_passed=not reasons, reasons=tuple(reasons))


def running_pressure(samples: list[HostSample], now: float) -> str:
    """Pure watchdog decision; it cannot stop anything. A live watchdog is still required."""
    policy = AdmissionPolicy()
    if (
        not samples
        or not 0 <= now - samples[-1].sampled_at <= policy.watchdog_heartbeat_timeout_seconds
        or any(
            not 0 < b.sampled_at - a.sampled_at <= 2
            for a, b in zip(samples, samples[1:], strict=False)
        )
    ):
        return "abort_owned_vm_only_telemetry_stale_or_missing"
    latest = samples[-1]
    if latest.available_bytes < policy.critical_available_mib * MIB:
        return "abort_owned_vm_only_critical_ram"
    if latest.model_runtime_absent is not True:
        return "abort_owned_vm_only_model_overlap_or_unknown"
    tail = [s for s in samples if now - s.sampled_at <= policy.sustained_pressure_seconds]
    if len(tail) >= 6 and tail[-1].sampled_at - tail[0].sampled_at >= 5:
        if all(
            s.available_bytes < policy.running_available_mib_min * MIB
            or s.commit_percent > policy.running_commit_percent_max
            or s.cpu_percent > policy.running_cpu_percent_max
            for s in tail
        ):
            return "abort_owned_vm_only_sustained_pressure"
    if (
        latest.system_disk_free_bytes < policy.system_disk_free_mib_min * MIB
        or latest.worker_disk_free_bytes < policy.worker_disk_free_mib_min * MIB
    ):
        return "abort_owned_vm_only_disk_pressure"
    return "continue_observation_only"


def capacity_assessment(candidate_memory_mib: int = 512) -> dict[str, object]:
    # This is an engineering reservation, NOT a benchmark or an Alpine minimum.
    # The readonly image/page cache, kernel, trusted controller and tools need RAM
    # outside the candidate cgroup. No swap or dynamic-memory workaround is allowed.
    reservation = 128
    margin = 64
    fits_reservation = 64 <= candidate_memory_mib <= 512 - reservation - margin
    return {
        "guest_memory_mib": 512,
        "virtual_processors": 1,
        "candidate_memory_mib": candidate_memory_mib,
        "OS_tools_controller_reservation_mib": reservation,
        "safety_margin_mib": margin,
        "fits_static_reservation": fits_reservation,
        "reservation_is_measured": False,
        "guest_fit_verified": False,
        "existing_contract_default_supported": False,
        "reason": (
            "requires_measured_boot_and_peak_workload"
            if fits_reservation
            else "candidate_plus_guest_reservation_exceeds_fixed_VM_RAM"
        ),
    }


def qualification_plan() -> dict[str, object]:
    """Reviewable jobs only, including a separate cancellation phase. No host execution."""
    cases = []
    for probe in preserved_probes():
        phases: tuple[Literal["main", "cancel"], ...] = (
            ("main", "cancel") if probe.name == "cpu_deadline_and_cancellation" else ("main",)
        )
        for phase in phases:
            job = probe_job(probe.name, phase)
            cases.append(
                {
                    "probe": probe.name,
                    "phase": phase,
                    "payload_sha256": probe.source_sha256,
                    "required_memory_mib": job.memory_mib,
                    "cpu_millis": job.cpu_millis,
                    "timeout_seconds": job.timeout_seconds,
                    "capacity": capacity_assessment(job.memory_mib),
                    "job": job.model_dump(),
                }
            )
    return {
        "status": "preparation_only_not_authorization",
        "production_execution_enabled": False,
        "vm_operations_authorized": False,
        "live_probes_executed": 0,
        "jobs_are_ephemeral_review_data": True,
        "must_regenerate_jobs_after_authorization": True,
        "first_failure": "stop_dispatch_preserve_evidence_teardown_exact_owned_VM",
        "cases": cases,
        "required_sequence": [
            "explicit_per_run_owner_authorization",
            "fresh_host_admission_window_and_exclusive_model_worker_lease",
            "verify_image_tool_manifest_and_controller_digests",
            "record_existing_VM_inventory_readonly_and_unique_creation_intent",
            "create_one_new_VM_off_persist_exact_VM_ID_before_start",
            "independent_watchdog_armed_and_tested_before_start",
            "verify_effective_512MiB_one_CPU_no_NIC_VHD_shares_passthrough",
            "bounded_boot_with_serial_challenge_trusted_tools_and_cgroup_v2_attestation",
            "measure_idle_and_peak_guest_RAM_reject_global_OOM_or_missing_margin",
            "six_cases_plus_after_start_cancellation_sequentially_no_model_concurrency",
            "bind_observations_receipts_to_run_nonce_image_controller_and_VM_ID",
            "kill_job_cgroup_verify_no_survivors_unmount_writable_job_state",
            "simulate_controller_loss_watchdog_stops_only_owned_VM_no_execution_replay",
            "confirm_owned_VM_Off_remove_exact_ID_confirm_absence_inventory_unchanged",
            "retain_media_journal_and_evidence_no_recursive_file_deletion",
            "manual_review_real_evidence_production_gate_remains_disabled",
        ],
    }
