"""Controller tests only: Podman/process outputs are synthetic, candidate code never runs."""

import io
import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_worker_contract import KEY, job, receipt

from repopilot.policy import PolicyError, digest
from repopilot.sandbox import LinuxSandbox
from repopilot.worker_contract import COMMANDS, VerificationJob, WorkerCheck, sign
from repopilot.worker_server import WorkerManager, routes

IMAGE = "sha256:" + "a" * 64


def driver(tmp_path):
    return LinuxSandbox(IMAGE, str(tmp_path / "podman"), str(tmp_path / "runsc"))


def test_runtime_needs_pinned_local_image_and_preflight(tmp_path):
    with pytest.raises(PolicyError):
        LinuxSandbox("python:latest")
    with pytest.raises(PolicyError):
        LinuxSandbox(IMAGE, "podman")
    with pytest.raises(PolicyError, match="preflight_required"):
        driver(tmp_path).run(job(), threading.Event())
    legacy = job().model_dump()
    legacy["profile"] = "python-checks-v1"
    with pytest.raises(ValueError):
        VerificationJob.model_validate(legacy)


def test_command_enforces_scope_limits_and_no_secret_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key-not-for-guests")
    monkeypatch.setenv("CONTAINER_HOST", "tcp://untrusted.example")
    runtime = driver(tmp_path)
    command = runtime.arguments(job(), "pytest")
    assert "--network=none" in command and "--user=65532:65532" in command
    assert "--pids-limit=32" in command and "--memory=512m" in command
    assert "--cpus=1.0" in command and "--pull=never" in command
    assert "--read-only-tmpfs=false" in command and "--unsetenv-all" in command
    assert "--security-opt=no-new-privileges" in command and "--image-volume=ignore" in command
    assert "--runtime" in command and runtime.runsc in command
    assert not any(
        x.startswith(("--mount", "--volume", "--privileged", "--device")) for x in command
    )
    assert "OPENAI_API_KEY" not in runtime.env and "CONTAINER_HOST" not in runtime.env
    assert COMMANDS["pytest"][-1] == "."  # Root-level fixture tests are included.
    with pytest.raises(PolicyError, match="command_not_allowed"):
        runtime.arguments(job(), "sh")


@pytest.mark.parametrize("failure", [None, "rootful", "v1", "controllers", "image"])
def test_preflight_fails_closed_on_unenforceable_host(tmp_path, monkeypatch, failure):
    runtime = driver(tmp_path)
    for path in (runtime.podman, runtime.runsc):
        Path(path).touch()
    monkeypatch.setattr("repopilot.sandbox.sys.platform", "linux")
    monkeypatch.setattr("repopilot.sandbox.os.geteuid", lambda: 1000, raising=False)
    monkeypatch.setattr("repopilot.sandbox.os.access", lambda *a: True)
    host = {
        "security": {"rootless": failure != "rootful"},
        "cgroupVersion": "v1" if failure == "v1" else "v2",
        "cgroupControllers": [] if failure == "controllers" else ["cpu", "memory", "pids"],
    }

    def control(args):
        data = {"host": host} if args[0] == "info" else [{"Id": IMAGE}]
        return subprocess.CompletedProcess(
            args,
            1 if failure == "image" and args[0] == "image" else 0,
            json.dumps(data).encode(),
            b"",
        )

    monkeypatch.setattr(runtime, "control", control)
    if failure:
        with pytest.raises(PolicyError):
            runtime.preflight()
        assert runtime.checked is False
    else:
        assert runtime.preflight()["isolated"] == "unverified"
        assert runtime.checked is True


@pytest.mark.parametrize("mode", ["success", "overflow", "cancel", "timeout"])
def test_command_captures_exit_and_bounds_output_without_running_code(tmp_path, monkeypatch, mode):
    runtime, cancel = driver(tmp_path), threading.Event()

    class Process:
        pid = 123
        returncode = None
        stdout = io.BytesIO(b"x" * (16001 if mode == "overflow" else 12))
        stdin = io.BytesIO()

        def poll(self):
            if mode == "success":
                self.returncode = 0
            return self.returncode

        def wait(self, timeout):
            return self.returncode

    proc = Process()
    monkeypatch.setattr("repopilot.sandbox.subprocess.Popen", lambda *a, **kw: proc)
    monkeypatch.setattr(runtime, "control", lambda args: subprocess.CompletedProcess(args, 0))
    monkeypatch.setattr(runtime, "verify_container", lambda *args: None)
    monkeypatch.setattr(runtime, "stop", lambda pid: setattr(proc, "returncode", -9))
    if mode == "cancel":
        cancel.set()
    result = runtime.command(
        job(), "pytest", cancel, time.monotonic() + (-1 if mode == "timeout" else 2)
    )
    assert len(result.output) <= 16000
    assert (result.exit_code == 0) == (mode == "success")
    assert result.timed_out == (mode == "timeout")
    assert result.cancelled == (mode == "cancel")


@pytest.mark.parametrize("failure", [False, True])
def test_runtime_requires_confirmed_cleanup_before_receipt(tmp_path, monkeypatch, failure):
    runtime = driver(tmp_path)
    runtime.checked = True
    monkeypatch.setattr(
        runtime,
        "command",
        lambda j, name, *a: WorkerCheck(
            name=name,
            command=COMMANDS[name],
            exit_code=0,
            output="synthetic check",
            duration_seconds=0.1,
        ),
    )
    calls = []

    def control(args):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0 if failure or args[0] == "rm" else 1)

    monkeypatch.setattr(runtime, "control", control)
    if failure:
        with pytest.raises(PolicyError, match="cleanup_unconfirmed"):
            runtime.run(job(), threading.Event())
    else:
        assert runtime.run(job(), threading.Event()).outcome == "completed"
        assert len(calls) == 6


class Runtime:
    def __init__(self):
        self.calls = 0
        self.started = threading.Event()
        self.wait = False
        self.fail = False
        self.cleaned = []

    def cleanup(self, order):
        self.cleaned.append(order.run_id)

    def run(self, order, cancel):
        self.calls += 1
        self.started.set()
        if self.wait:
            assert cancel.wait(3)
        if self.fail:
            raise RuntimeError("sensitive detail must not cross HTTP boundary")
        from repopilot.worker_contract import ExecutionReceipt

        return ExecutionReceipt.model_validate(
            receipt(order, outcome="cancelled" if cancel.is_set() else "completed").payload
        )


def manager(tmp_path):
    runtime = Runtime()
    return WorkerManager(tmp_path / "journal.db", KEY, runtime), runtime


def test_worker_http_authentication_replay_and_body_limits(tmp_path):
    service, runtime = manager(tmp_path)
    envelope = sign(job().model_dump(), KEY, "job")
    with TestClient(routes(service)) as client:
        assert client.get("/health").status_code == 200
        assert client.post("/v1/no-shell", json={}).status_code == 404
        assert client.post("/v1/execute", content=b"x" * 256001).status_code == 413
        assert (
            client.post("/v1/execute", json={"payload": {}, "signature": "0" * 64}).status_code
            == 409
        )
        first = client.post("/v1/execute", json=envelope.model_dump())
        assert first.status_code == 200
        assert client.post("/v1/execute", json=envelope.model_dump()).json() == first.json()
        assert runtime.calls == 1
        changed = envelope.payload | {"nonce": "f" * 32}
        assert (
            client.post("/v1/execute", json=sign(changed, KEY, "job").model_dump()).status_code
            == 409
        )


def test_worker_concurrent_claim_cancellation_and_durable_replay(tmp_path):
    service, runtime = manager(tmp_path)
    runtime.wait = True
    order = job()
    envelope = sign(order.model_dump(), KEY, "job")
    cancellation = sign(
        {
            "run_id": order.run_id,
            "nonce": order.nonce,
            "job_digest": digest(order.model_dump()),
            "expires_at": order.expires_at,
        },
        KEY,
        "cancel",
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        future = pool.submit(service.execute, envelope)
        assert runtime.started.wait(2)
        with pytest.raises(PolicyError, match="no_replay"):
            service.execute(envelope)
        cancelled = service.cancel(cancellation)
        assert cancelled.payload["outcome"] == "cancelled"
        assert future.result() == cancelled
    restarted = WorkerManager(service.database, KEY, runtime)
    restarted.recover()
    assert restarted.execute(envelope) == cancelled
    assert restarted.cancel(cancellation) == cancelled
    assert runtime.calls == 1


def test_interruption_recovery_cleans_containers_without_reexecution(tmp_path):
    service, runtime = manager(tmp_path)
    runtime.fail = True
    order = job()
    envelope = sign(order.model_dump(), KEY, "job")
    with pytest.raises(PolicyError, match="interrupted"):
        service.execute(envelope)
    service.recover()
    assert runtime.cleaned == [order.run_id]
    with pytest.raises(PolicyError, match="no_replay"):
        service.execute(envelope)
    assert runtime.calls == 1
    with service.connect() as conn:
        assert conn.execute("SELECT state FROM jobs").fetchone()[0] == "recovered"


def test_guest_and_controller_command_profiles_match():
    import runpy

    trusted_guest = runpy.run_path("deploy/worker/bootstrap.py", run_name="profile_contract")
    assert trusted_guest["COMMANDS"] == COMMANDS


@pytest.mark.parametrize("change", [None, "runtime", "mount", "network", "memory", "root"])
def test_inspect_rejects_effective_runtime_or_mount_overrides(tmp_path, monkeypatch, change):
    runtime, order = driver(tmp_path), job()
    item = {
        "OCIRuntime": "runsc",
        "Config": {"User": "65532:65532"},
        "Mounts": [],
        "HostConfig": {
            "Privileged": False,
            "ReadonlyRootfs": True,
            "NetworkMode": "none",
            "Memory": 512 * 1048576,
            "MemorySwap": 512 * 1048576,
            "PidsLimit": 32,
            "NanoCpus": 1000000000,
        },
    }
    if change == "runtime":
        item["OCIRuntime"] = "runc"
    if change == "mount":
        item["Mounts"] = [{"Type": "bind", "Source": "/"}]
    if change == "network":
        item["HostConfig"]["NetworkMode"] = "host"
    if change == "memory":
        item["HostConfig"]["Memory"] = 0
    if change == "root":
        item["Config"]["User"] = "0"
    monkeypatch.setattr(
        runtime,
        "control",
        lambda args: subprocess.CompletedProcess(args, 0, json.dumps([item]).encode()),
    )
    if change:
        with pytest.raises(PolicyError, match="effective_configuration"):
            runtime.verify_container(order, "pytest")
    else:
        runtime.verify_container(order, "pytest")
