"""Synthetic admission/plan tests only. No VM, Linux command or probe payload runs."""

import subprocess

import pytest

from repopilot.hyperv_preparation import (
    MIB,
    AdmissionPolicy,
    HostSample,
    admission,
    capacity_assessment,
    qualification_plan,
    running_pressure,
)
from repopilot.isolation_probes import PROBE_NAMES, preserved_probes
from repopilot.worker_contract import DisabledWorker


def samples(count=16, spacing=2, **changes):
    return [
        HostSample(
            **{
                "sampled_at": float(100 + n * spacing),
                "available_bytes": 3072 * MIB,
                "commit_headroom_bytes": 4096 * MIB,
                "commit_percent": 60.0,
                "cpu_percent": 20.0,
                "system_disk_free_bytes": 8192 * MIB,
                "worker_disk_free_bytes": 16384 * MIB,
                "model_runtime_absent": True,
                **changes,
            }
        )
        for n in range(count)
    ]


def test_sustained_resources_cannot_authorize_execution():
    result = admission(samples(), 130.0)
    assert result.resource_checks_passed
    assert not result.vm_operations_authorized
    assert not result.production_execution_enabled
    assert not DisabledWorker.available
    assert AdmissionPolicy().start_available_mib == 2048


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"available_bytes": 2048 * MIB - 1}, "available_ram_below_2048_MiB"),
        ({"commit_headroom_bytes": 2048 * MIB - 1}, "commit_headroom_or_load_failed"),
        ({"commit_percent": 85.01}, "commit_headroom_or_load_failed"),
        ({"cpu_percent": 80.01}, "host_cpu_above_80_percent"),
        ({"system_disk_free_bytes": 4096 * MIB - 1}, "C_or_D_free_space_below_4096_MiB"),
        ({"worker_disk_free_bytes": 4096 * MIB - 1}, "C_or_D_free_space_below_4096_MiB"),
        ({"model_runtime_absent": None}, "model_runtime_absence_unconfirmed"),
        ({"model_runtime_absent": False}, "model_runtime_absence_unconfirmed"),
    ],
)
def test_one_bad_sample_denies_admission(changes, reason):
    readings = samples()
    readings[8] = HostSample(**{**readings[8].model_dump(), **changes})
    result = admission(readings, 130.0)
    assert not result.resource_checks_passed
    assert reason in result.reasons


@pytest.mark.parametrize(
    ("readings", "now"),
    [([], 130.0), (samples(count=15), 128.0), (samples(), 134.0), (samples(), 129.0)],
)
def test_missing_short_stale_and_future_window_denied(readings, now):
    assert not admission(readings, now).resource_checks_passed


def test_gap_and_out_of_order_readings_denied():
    readings = samples()
    readings[8] = readings[7]
    assert not admission(readings, 130.0).resource_checks_passed
    readings[8] = readings[10]
    assert not admission(readings, 130.0).resource_checks_passed


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"available_bytes": 511 * MIB}, "critical_ram"),
        ({"model_runtime_absent": None}, "model_overlap_or_unknown"),
        ({"system_disk_free_bytes": 4095 * MIB}, "disk_pressure"),
        ({"worker_disk_free_bytes": 4095 * MIB}, "disk_pressure"),
    ],
)
def test_watchdog_decisions_target_only_owned_VM(changes, reason):
    assert running_pressure(samples(count=1, **changes), 100.0) == "abort_owned_vm_only_" + reason


def test_watchdog_critical_stale_and_sustained_pressure():
    assert running_pressure([], 130.0).endswith("telemetry_stale_or_missing")
    assert running_pressure(samples(), 134.0).endswith("telemetry_stale_or_missing")
    for changes in (
        {"available_bytes": 767 * MIB},
        {"commit_percent": 91.0},
        {"cpu_percent": 96.0},
    ):
        readings = samples(count=6, spacing=1, **changes)
        assert running_pressure(readings, 105.0).endswith("sustained_pressure")
        assert running_pressure(readings[:-1], 104.0) == "continue_observation_only"
    assert running_pressure(samples(), 130.0) == "continue_observation_only"


def test_512_MiB_guest_cannot_guarantee_default_512_MiB_candidate():
    assert not capacity_assessment()["fits_static_reservation"]
    small = capacity_assessment(128)
    assert small["fits_static_reservation"]
    assert not small["guest_fit_verified"]
    assert not small["reservation_is_measured"]
    assert not small["existing_contract_default_supported"]


def test_exact_six_probe_payloads_and_cancellation_are_prepared_never_executed(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No process is permitted in qualification preparation")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    plan = qualification_plan()
    assert plan["live_probes_executed"] == 0
    assert not plan["vm_operations_authorized"]
    cases = plan["cases"]
    assert [case["probe"] for case in cases] == [*PROBE_NAMES, PROBE_NAMES[-1]]
    assert [case["phase"] for case in cases] == ["main"] * 6 + ["cancel"]
    payloads = {p.name: p.source for p in preserved_probes()}
    for case in cases:
        assert case["job"]["files"] == {"test_boundary.py": payloads[case["probe"]]}
        assert not case["capacity"]["guest_fit_verified"]
    assert sum(case["capacity"]["fits_static_reservation"] for case in cases) == 1
    assert not DisabledWorker.available
