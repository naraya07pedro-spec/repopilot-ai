"""Trusted disposable-host harness. Run inside an unprivileged delegated systemd scope.

Only the controller runs here. Candidate code continues to run exclusively in runsc.
No privilege escalation, cgroup permission changes, or ignored limit failures are allowed.
"""

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if sys.platform != "linux" or os.geteuid() == 0:
        raise SystemExit("requires unprivileged disposable Linux scope")
    relative = Path("/proc/self/cgroup").read_text().strip().removeprefix("0::")
    root = Path("/sys/fs/cgroup")
    scope = (root / relative.lstrip("/")).resolve()
    if not scope.is_relative_to(root) or not scope.name.endswith(".scope"):
        raise SystemExit("requires dedicated delegated systemd scope")
    controller = scope / "repopilot-controller"
    jobs = scope / "repopilot-jobs"
    controller.mkdir()
    (controller / "cgroup.procs").write_text(str(os.getpid()))
    # The delegation root must have no internal processes before enabling controllers.
    if (scope / "cgroup.procs").read_text().strip():
        raise SystemExit("delegated scope still has internal processes")
    (scope / "cgroup.subtree_control").write_text("+cpu +memory +pids")
    jobs.mkdir()
    (jobs / "cgroup.subtree_control").write_text("+cpu +memory +pids")
    print(
        "Delegated cgroupfs controllers:", (jobs / "cgroup.subtree_control").read_text(), flush=True
    )
    env = os.environ | {"REPOPILOT_WORKER_CGROUP_PARENT": str(jobs)}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_sandbox_live.py",
            "-v",
            "-s",
            "--junitxml=evidence/sandbox-live.xml",
        ],
        env=env,
        check=False,
    )
    # Do not hide leaked objects by deleting them. Keep the failure and raw JUnit evidence.
    remaining = subprocess.run(
        [
            "/usr/bin/podman",
            "--remote=false",
            "--cgroup-manager=cgroupfs",
            "ps",
            "-aq",
            "--filter",
            "name=rp-",
        ],
        capture_output=True,
        check=False,
    )
    if remaining.returncode or remaining.stdout.strip() or any(p.is_dir() for p in jobs.iterdir()):
        return 1
    print("Probe container objects absent after cleanup", flush=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
