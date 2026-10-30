"""Linux-only rootless Podman/runsc driver. Not activated by the owner application.

Actual isolation remains unverified until the opt-in live harness passes on the host.
Only the container runtime is invoked on the controller; candidate code is stdin data.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Literal

from repopilot.policy import PolicyError, digest, redact
from repopilot.worker_contract import COMMANDS, ExecutionReceipt, VerificationJob, WorkerCheck


class LinuxSandbox:
    def __init__(
        self, image: str, podman: str = "/usr/bin/podman", runsc: str = "/usr/local/bin/runsc"
    ):
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
            raise PolicyError("sandbox_requires_local_image_digest")
        if not all(Path(p).is_absolute() for p in (podman, runsc)):
            raise PolicyError("sandbox_requires_absolute_runtime_paths")
        self.image, self.podman, self.runsc = image, podman, runsc
        # Never inherit model keys, App credentials, proxies or remote Podman configuration.
        self.env = {k: os.environ[k] for k in ("HOME", "XDG_RUNTIME_DIR") if k in os.environ}
        self.env.update(PATH="/usr/local/bin:/usr/bin:/bin", LANG="C.UTF-8")
        self.checked = False

    def control(self, args: list[str]) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [self.podman, "--remote=false", *args],
            env=self.env,
            capture_output=True,
            timeout=10,
            check=False,
        )

    def preflight(self) -> dict[str, Any]:
        if sys.platform != "linux" or os.geteuid() == 0:
            raise PolicyError("sandbox_requires_nonroot_linux")
        if not all(Path(p).is_file() and os.access(p, os.X_OK) for p in (self.podman, self.runsc)):
            raise PolicyError("sandbox_runtime_missing")
        response = self.control(["info", "--format=json"])
        if response.returncode or len(response.stdout) > 1048576:
            raise PolicyError("sandbox_preflight_failed")
        host = json.loads(response.stdout)["host"]
        if (
            host["security"]["rootless"] is not True
            or host["cgroupVersion"] != "v2"
            or not {"cpu", "memory", "pids"}.issubset(host["cgroupControllers"])
        ):
            raise PolicyError("sandbox_cgroup_or_rootless_unavailable")
        inspected = self.control(["image", "inspect", self.image])
        if inspected.returncode:
            raise PolicyError("sandbox_image_missing_no_automatic_pull")
        metadata = json.loads(inspected.stdout)[0]
        if metadata["Id"].removeprefix("sha256:") != self.image.removeprefix("sha256:"):
            raise PolicyError("sandbox_image_identity")
        self.checked = True
        return {
            "rootless": True,
            "cgroup_version": "v2",
            "image": self.image,
            "isolated": "unverified",
        }

    @staticmethod
    def name(job: VerificationJob, check: str) -> str:
        return f"rp-{job.run_id}-{job.nonce}-{check}"

    def arguments(self, job: VerificationJob, check: str) -> list[str]:
        if check not in COMMANDS:
            raise PolicyError("sandbox_command_not_allowed")
        # All writable space is bounded tmpfs; no bind mounts, sockets, devices or host namespace.
        return [
            self.podman,
            "--remote=false",
            "--runtime",
            self.runsc,
            "create",
            "--name",
            self.name(job, check),
            "--pull=never",
            "--restart=no",
            "--network=none",
            "--no-hosts",
            "--http-proxy=false",
            "--unsetenv-all",
            "--read-only",
            "--read-only-tmpfs=false",
            "--image-volume=ignore",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--user=65532:65532",
            "--pid=private",
            "--ipc=private",
            "--uts=private",
            "--cgroupns=private",
            f"--memory={job.memory_mib}m",
            f"--memory-swap={job.memory_mib}m",
            f"--cpus={job.cpu_millis / 1000}",
            f"--pids-limit={job.process_limit}",
            "--ulimit=nofile=128:128",
            "--ulimit=core=0:0",
            "--log-driver=none",
            "--health-cmd=none",
            "--sdnotify=ignore",
            f"--tmpfs=/work:rw,noexec,nosuid,nodev,size={job.disk_mib - 4}m,"
            "uid=65532,gid=65532,mode=700",
            "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=4m,uid=65532,gid=65532,mode=700",
            "--workdir=/work",
            "--entrypoint=/opt/tools/bin/python",
            "-i",
            self.image,
            "-I",
            "-B",
            "/opt/bootstrap.py",
            check,
        ]

    def cleanup(self, job: VerificationJob) -> None:
        for check in COMMANDS:
            name = self.name(job, check)
            self.control(["rm", "--force", "--time=0", name])
            # 'exists' returns 1 only when absent; runtime errors are not proof of cleanup.
            if self.control(["container", "exists", name]).returncode != 1:
                raise PolicyError("sandbox_cleanup_unconfirmed")

    def command(
        self,
        job: VerificationJob,
        check: Literal["pytest", "lint", "format"],
        cancel: threading.Event,
        deadline: float,
    ) -> WorkerCheck:
        started = time.monotonic()
        created = self.control(self.arguments(job, check)[2:])
        if created.returncode:
            raise PolicyError("sandbox_create_failed")
        self.verify_container(job, check)
        output = bytearray()
        overflow = threading.Event()
        process = subprocess.Popen(
            [
                self.podman,
                "--remote=false",
                "start",
                "--attach",
                "--interactive",
                self.name(job, check),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=self.env,
            start_new_session=True,
        )
        assert process.stdout and process.stdin

        def read() -> None:
            assert process.stdout
            while chunk := process.stdout.read(4096):
                room = 16000 - len(output)
                output.extend(chunk[:room])
                if len(chunk) > room:
                    overflow.set()

        def write() -> None:
            assert process.stdin
            try:
                process.stdin.write(json.dumps(job.files).encode())
                process.stdin.close()
            except (BrokenPipeError, OSError):
                pass

        reader, writer = (
            threading.Thread(target=read, daemon=True),
            threading.Thread(target=write, daemon=True),
        )
        reader.start()
        writer.start()
        timed_out = False
        try:
            while process.poll() is None:
                timed_out = time.monotonic() >= deadline
                if timed_out or cancel.is_set() or overflow.is_set():
                    self.control(["kill", self.name(job, check)])
                    self.stop(process.pid)
                    break
                time.sleep(0.02)
            code = process.wait(timeout=5)
        finally:
            if process.poll() is None:
                self.stop(process.pid)
                process.wait(timeout=5)
            reader.join(timeout=2)
            writer.join(timeout=2)
            process.stdout.close()
        if reader.is_alive() or writer.is_alive():
            raise PolicyError("sandbox_pipe_cleanup_unconfirmed")
        return WorkerCheck(
            name=check,
            command=COMMANDS[check],
            exit_code=1 if overflow.is_set() else (code if code >= 0 else 128 - code),
            output=redact(output.decode("utf-8", errors="replace")),
            duration_seconds=time.monotonic() - started,
            timed_out=timed_out,
            cancelled=cancel.is_set(),
        )

    def verify_container(self, job: VerificationJob, check: str) -> None:
        response = self.control(["inspect", self.name(job, check)])
        if response.returncode:
            raise PolicyError("sandbox_inspection_failed")
        item = json.loads(response.stdout)[0]
        host = item["HostConfig"]
        cpu = host.get("NanoCpus", 0) or (
            host.get("CpuQuota", 0) * 1000000000 / (host.get("CpuPeriod", 0) or 1)
        )
        if (
            item["OCIRuntime"] != "runsc"
            or item["Config"]["User"] != "65532:65532"
            or host["Privileged"] is not False
            or host["ReadonlyRootfs"] is not True
            or host["NetworkMode"] != "none"
            or host["Memory"] != job.memory_mib * 1048576
            or host["MemorySwap"] != job.memory_mib * 1048576
            or host["PidsLimit"] != job.process_limit
            or cpu != job.cpu_millis * 1000000
            or any(m["Type"] != "tmpfs" for m in item.get("Mounts", []))
            or host.get("Binds")
        ):
            raise PolicyError("sandbox_effective_configuration_rejected")

    @staticmethod
    def stop(pid: int) -> None:
        try:
            if hasattr(os, "killpg"):
                os.killpg(pid, 9)  # POSIX SIGKILL; Linux preflight is mandatory.
            else:
                raise PolicyError("sandbox_requires_linux_process_groups")
        except ProcessLookupError:
            pass

    def run(self, job: VerificationJob, cancel: threading.Event) -> ExecutionReceipt:
        if not self.checked:
            raise PolicyError("sandbox_preflight_required")
        job = VerificationJob.model_validate(job.model_dump())
        if not job.issued_at <= time.time() <= job.expires_at:
            raise PolicyError("worker_lease_expired")
        deadline = time.monotonic() + job.timeout_seconds
        checks: list[WorkerCheck] = []
        try:
            for check in ("pytest", "lint", "format"):
                if cancel.is_set() or time.monotonic() >= deadline:
                    break
                result = self.command(job, check, cancel, deadline)
                checks.append(result)
                if result.timed_out or result.cancelled:
                    break
        finally:
            self.cleanup(job)  # No receipt can report success before confirmed teardown.
        passed = len(checks) == 3 and all(c.exit_code == 0 and not c.timed_out for c in checks)
        return ExecutionReceipt(
            run_id=job.run_id,
            nonce=job.nonce,
            job_digest=digest(job.model_dump()),
            outcome="cancelled" if cancel.is_set() else "completed" if passed else "failed",
            checks=checks,
        )
