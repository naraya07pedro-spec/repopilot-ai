"""Small, secret-free WSL prerequisite audit; never executes repository/model code.

No packages, models, application files, settings or network connections are created.
Optional probes start fixed trusted commands and transient systemd units (journal
entries may remain). They are NOT hostile-code isolation tests.
"""

import argparse
import configparser
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path


def read(path: str) -> str:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return ""


def command(argv: list[str], timeout: int = 10) -> dict[str, object]:
    started = time.monotonic()
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout[:4096].strip(),
            "stderr": result.stderr[:2048].strip(),
            "duration_seconds": round(time.monotonic() - started, 3),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": type(exc).__name__}


def report(probes: bool) -> dict[str, object]:
    memory = {
        line.split(":")[0]: int(line.split()[1]) * 1024
        for line in read("/proc/meminfo").splitlines()
        if line.split(":")[0] in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
    }
    cfg = configparser.ConfigParser()
    cfg.read("/etc/wsl.conf")
    root_disk = shutil.disk_usage("/")
    cg = Path("/sys/fs/cgroup")
    user_service = command(
        ["systemctl", "show", f"user@{os.getuid()}.service", "-p", "Delegate", "-p", "ControlGroup"]
    )
    result: dict[str, object] = {
        "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "os": platform.freedesktop_os_release().get("PRETTY_NAME"),
        "uid": os.getuid(),
        "logical_processors": os.cpu_count(),
        "memory_bytes": memory,
        "root_filesystem": {
            "total_bytes": root_disk.total,
            "free_bytes": root_disk.free,
            "thin_vhd_not_physical_host_free_space": True,
        },
        "pid1": read("/proc/1/comm"),
        "tools": {
            name: shutil.which(name) is not None
            for name in (
                "python3",
                "node",
                "ollama",
                "podman",
                "docker",
                "runsc",
                "unshare",
                "newuidmap",
                "newgidmap",
            )
        },
        "cgroup_v2": (cg / "cgroup.controllers").exists(),
        "cgroup_controllers": read(str(cg / "cgroup.controllers")).split(),
        "root_subtree_controllers": read(str(cg / "cgroup.subtree_control")).split(),
        "root_cgroup_writable": os.access(cg / "cgroup.subtree_control", os.W_OK),
        "user_service": user_service,
        "kvm_device_present": Path("/dev/kvm").exists(),
        "kvm_accessible_to_current_user": os.access("/dev/kvm", os.R_OK | os.W_OK),
        "windows_drive_c_mounted": os.path.ismount("/mnt/c"),
        "windows_interop_registered": Path("/proc/sys/fs/binfmt_misc/WSLInterop").exists(),
        "configured_automount_enabled": cfg.getboolean("automount", "enabled", fallback=True),
        "configured_interop_enabled": cfg.getboolean("interop", "enabled", fallback=True),
        "configured_systemd": cfg.getboolean("boot", "systemd", fallback=False),
        "sandbox_verified": False,
        "audit_authorizes_owner_execution": False,
        "installs_or_external_network_calls": False,
    }
    if not probes:
        return result
    result["namespace_probe"] = command(
        ["unshare", "--user", "--map-root-user", "--net", "/bin/true"], timeout=5
    )
    # Read actual kernel settings in a small, non-root, secret-free child service.
    # No stress load; this proves configured limits, NOT adversarial enforcement.
    unit = "repopilot-audit-" + uuid.uuid4().hex
    child = """import json, os
from pathlib import Path
relative = Path('/proc/self/cgroup').read_text().strip().split('::', 1)[1].lstrip('/')
cg = Path('/sys/fs/cgroup') / relative
status = Path('/proc/self/status').read_text().splitlines()
print(json.dumps({
    'uid': os.getuid(),
    'limits': {name: (cg/name).read_text().strip()
        for name in ('cpu.max', 'memory.max', 'memory.swap.max', 'pids.max')},
    'no_new_privs': next(line.split(':')[1].strip()
        for line in status if line.startswith('NoNewPrivs:'))
}))
"""
    try:
        result["transient_cgroup_probe"] = command(
            [
                "systemd-run",
                "--user",
                "--quiet",
                "--wait",
                "--pipe",
                "--collect",
                f"--unit={unit}",
                "--property=MemoryMax=64M",
                "--property=MemorySwapMax=0",
                "--property=TasksMax=16",
                "--property=CPUQuota=25%",
                "--property=NoNewPrivileges=yes",
                sys.executable,
                "-c",
                child,
            ]
        )
    finally:
        command(["systemctl", "--user", "stop", unit])
    result["transient_service_active_after_cleanup"] = command(
        ["systemctl", "--user", "is-active", unit]
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probes", action="store_true", help="fixed namespace/cgroup probes only")
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("Run inside WSL/Linux using its Python 3.12+; no installation is performed")
    if args.probes and os.getuid() == 0:
        parser.error("Run prerequisite probes as the non-root Linux owner")
    print(json.dumps(report(args.probes), indent=2))
