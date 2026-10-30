"""Opt-in destructive-resource probes, only inside a dedicated disposable Linux test VM.

These tests never fall back to executing candidate code on the test controller.
Normal CI skips them because it does not supply a reviewed rootless runsc host.
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_worker_contract import job

from repopilot.sandbox import LinuxSandbox

pytestmark = pytest.mark.skipif(
    not os.environ.get("REPOPILOT_LIVE_SANDBOX_IMAGE")
    or os.environ.get("REPOPILOT_SANDBOX_ACK") != "disposable-test-host",
    reason="No explicitly approved disposable Linux/runsc test host",
)


@pytest.fixture
def runtime():
    instance = LinuxSandbox(os.environ["REPOPILOT_LIVE_SANDBOX_IMAGE"])
    instance.preflight()
    return instance


def run_source(runtime, source, **limits):
    order = job().model_copy(update={"files": {"test_boundary.py": source}, **limits})
    result = runtime.run(order, threading.Event())
    assert result.checks and result.checks[0].name == "pytest"
    return result


def test_live_benign_checks_and_teardown(runtime):
    result = run_source(runtime, "def test_answer():\n    assert 1 + 1 == 2\n")
    assert result.outcome == "completed", result.model_dump()
    assert all(c.exit_code == 0 for c in result.checks), result.model_dump()


def test_live_filesystem_identity_network_and_secret_boundary(runtime):
    result = run_source(
        runtime,
        """import os
import socket
from pathlib import Path


def test_boundary():
    assert os.getuid() == 65532
    assert Path.cwd().stat().st_uid == 65532
    assert Path.cwd().stat().st_mode & 0o777 == 0o700
    names = ("OPENAI_API_KEY", "GITHUB_APP_PRIVATE_KEY_FILE", "REPOPILOT_WORKER_KEY_FILE")
    assert not any(k in os.environ for k in names)
    assert not Path("/var/run/docker.sock").exists()
    assert not Path("/run/podman/podman.sock").exists()
    try:
        Path("/opt/escape").write_text("must not succeed")
    except OSError:
        pass
    else:
        raise AssertionError("root filesystem writable")
    for address in ("1.1.1.1", "169.254.169.254"):
        with socket.socket() as connection:
            connection.settimeout(1)
            assert connection.connect_ex((address, 80)) != 0
""",
    )
    assert result.checks[0].exit_code == 0, result.checks[0].output


def test_live_disk_limit(runtime):
    result = run_source(
        runtime,
        """def test_quota():
    try:
        with open("full", "wb") as target:
            for _ in range(80):
                target.write(b"x" * 1048576)
    except OSError as error:
        assert error.errno in (28, 122)
    else:
        raise AssertionError("disk quota did not reject 80 MiB")
""",
    )
    assert result.checks[0].exit_code == 0, result.checks[0].output


def test_live_memory_limit(runtime):
    result = run_source(
        runtime,
        """def test_memory():
    allocations = [bytearray(16 * 1048576) for _ in range(64)]
    assert len(allocations) == 64
""",
        memory_mib=128,
    )
    first = result.checks[0]
    assert first.exit_code == 137 or (first.exit_code != 0 and "MemoryError" in first.output), (
        first.model_dump()
    )
    assert result.outcome == "failed"


def test_live_process_limit(runtime):
    result = run_source(
        runtime,
        """import subprocess
import sys


def test_process_limit():
    children = []
    try:
        try:
            for _ in range(64):
                command = [sys.executable, "-I", "-c", "import time; time.sleep(5)"]
                children.append(subprocess.Popen(command))
        except OSError:
            assert len(children) < 64
        else:
            raise AssertionError("process limit not enforced")
    finally:
        for child in children:
            child.kill()
            child.wait()
""",
    )
    assert result.checks[0].exit_code == 0, result.checks[0].output


def test_live_cpu_deadline_and_cancellation(runtime):
    source = "def test_cpu():\n    while True:\n        pass\n"
    result = run_source(runtime, source, timeout_seconds=5)
    assert result.outcome == "failed" and result.checks[0].timed_out, result.model_dump()
    order = job().model_copy(update={"files": {"test_cpu.py": source}})
    cancel = threading.Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(runtime.run, order, cancel)
        threading.Event().wait(2)
        cancel.set()
        assert future.result(timeout=30).outcome == "cancelled"
