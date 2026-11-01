"""Bounded read-only Hyper-V host inventory and 30-second resource sampling.

No WSL, VM inventory/operations, UAC, service changes, credentials or network.
Only an optional NEW output file is written. A timed-out read-only child is killed;
no other process is signalled. Not an isolation test or worker admission authority.
"""

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

from repopilot.hyperv_preparation import HostSample, admission, capacity_assessment


class MemoryStatus(ctypes.Structure):
    _fields_ = [("length", wintypes.DWORD), ("load", wintypes.DWORD)] + [
        (name, ctypes.c_ulonglong)
        for name in (
            "physical_total",
            "physical_available",
            "pagefile_total",
            "pagefile_available",
            "virtual_total",
            "virtual_available",
            "extended_available",
        )
    ]


class PerformanceInfo(ctypes.Structure):
    _fields_ = (
        [("cb", wintypes.DWORD)]
        + [
            (name, ctypes.c_size_t)
            for name in (
                "commit_total",
                "commit_limit",
                "commit_peak",
                "physical_total",
                "physical_available",
                "system_cache",
                "kernel_total",
                "kernel_paged",
                "kernel_nonpaged",
                "page_size",
            )
        ]
        + [(name, wintypes.DWORD) for name in ("handles", "processes", "threads")]
    )


class ProcessEntry(ctypes.Structure):
    _fields_ = [
        ("size", wintypes.DWORD),
        ("usage", wintypes.DWORD),
        ("pid", wintypes.DWORD),
        ("heap", ctypes.c_size_t),
        ("module", wintypes.DWORD),
        ("threads", wintypes.DWORD),
        ("parent_pid", wintypes.DWORD),
        ("priority", wintypes.LONG),
        ("flags", wintypes.DWORD),
        ("name", wintypes.WCHAR * 260),
    ]


def model_processes() -> list[str]:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    if handle == wintypes.HANDLE(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    entry = ProcessEntry()
    entry.size = ctypes.sizeof(entry)
    found = set()
    known = {"llama-server.exe", "llama-cli.exe", "ollama.exe", "ollama_llama_server.exe"}
    try:
        ok = kernel.Process32FirstW(handle, ctypes.byref(entry))
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())
        while ok:
            if entry.name.casefold() in known:
                found.add(entry.name.casefold())
            ok = kernel.Process32NextW(handle, ctypes.byref(entry))
        if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(handle)
    return sorted(found)


def cpu_times() -> tuple[int, int]:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    idle, system, user = (wintypes.FILETIME() for _ in range(3))
    if not kernel.GetSystemTimes(ctypes.byref(idle), ctypes.byref(system), ctypes.byref(user)):
        raise ctypes.WinError(ctypes.get_last_error())

    def integer(value):
        return (value.dwHighDateTime << 32) | value.dwLowDateTime

    return integer(idle), integer(system) + integer(user)


def sample(previous: tuple[int, int]) -> tuple[HostSample, tuple[int, int], list[str]]:
    memory, performance = MemoryStatus(), PerformanceInfo()
    memory.length = ctypes.sizeof(memory)
    performance.cb = ctypes.sizeof(performance)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise OSError("GlobalMemoryStatusEx failed")
    if not ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(performance), performance.cb):
        raise OSError("GetPerformanceInfo failed")
    current = cpu_times()
    delta = current[1] - previous[1]
    if delta <= 0 or performance.commit_limit == 0:
        raise ValueError("invalid_resource_counters")
    processes = model_processes()
    return (
        HostSample(
            sampled_at=time.time(),
            available_bytes=memory.physical_available,
            commit_headroom_bytes=(performance.commit_limit - performance.commit_total)
            * performance.page_size,
            commit_percent=100.0 * performance.commit_total / performance.commit_limit,
            cpu_percent=max(0.0, min(100.0, 100 * (1 - (current[0] - previous[0]) / delta))),
            system_disk_free_bytes=shutil.disk_usage("C:/").free,
            worker_disk_free_bytes=shutil.disk_usage("D:/").free,
            model_runtime_absent=not processes,
        ),
        current,
        processes,
    )


def inventory() -> dict:
    script = Path(__file__).with_name("hyperv_readonly_inventory.ps1")
    executable = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    try:
        result = subprocess.run(
            [
                str(executable),
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "& '" + str(script).replace("'", "''") + "'",
            ],
            capture_output=True,
            timeout=25,
            check=True,
        )
        return {"status": "collected", "facts": json.loads(result.stdout.decode("utf-8-sig"))}
    except subprocess.TimeoutExpired:
        return {"status": "timed_out_after_25_seconds", "capability_verified": False}
    except subprocess.CalledProcessError as error:
        return {
            "status": "collection_failed",
            "capability_verified": False,
            "bounded_readonly_error": error.stderr.decode("utf-8-sig", errors="replace")[:2000],
        }
    except ValueError:
        return {"status": "collection_failed", "capability_verified": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Windows only")
    facts = inventory()
    samples, processes = [], set()
    previous = cpu_times()
    started = time.monotonic()
    # Native Win32 counters avoid WMI/service calls during the fixed sampling window.
    for index in range(16):
        time.sleep(max(0, started + 1 + 2.05 * index - time.monotonic()))
        current, previous, found = sample(previous)
        samples.append(current)
        processes.update(found)
    now = time.time()
    report = {
        "schema": "hyperv_preflight_v1",
        "measured_at_epoch": now,
        "inventory": facts,
        "samples": [s.model_dump() for s in samples],
        "admission": admission(samples, now).model_dump(),
        "known_model_process_names_found": sorted(processes),
        "model_absence_scope": "known_executable_names_only_exclusive_runtime_lease_still_required",
        "capacity": capacity_assessment(),
        "vm_operations_performed": False,
        "WSL_or_OpenClaw_operations_performed": False,
        "isolation_verified": False,
    }
    text = json.dumps(report, indent=2)
    if args.output:
        with args.output.open("x", encoding="utf-8") as output:
            output.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
