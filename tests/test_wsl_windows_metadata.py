"""The Windows metadata deadline must never act on an existing WSL process."""

import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

SPEC = importlib.util.spec_from_file_location(
    "windows_metadata",
    Path(__file__).resolve().parents[1] / "scripts/inspect_wsl_windows_metadata.py",
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def fake_worker(monkeypatch, *, timeouts=0, output=b""):
    class Worker:
        pid = 12345  # Newly created diagnostic worker, never a PID from input evidence.
        returncode = None

        def __init__(self, command, **kwargs):
            self.command = command
            self.waits = []
            self.killed = False
            kwargs["stdout"].write(output)

        def wait(self, *, timeout):
            self.waits.append(timeout)
            if len(self.waits) <= timeouts:
                raise subprocess.TimeoutExpired(self.command, timeout)
            self.returncode = -1 if self.killed else 0

        def kill(self):
            self.killed = True

    workers = []

    def start(*args, **kwargs):
        workers.append(Worker(*args, **kwargs))
        return workers[-1]

    monkeypatch.setattr(
        module, "os", SimpleNamespace(name="nt", environ={"SystemRoot": "C:/Windows"})
    )
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0, raising=False)
    monkeypatch.setattr(subprocess, "Popen", start)
    return workers


def test_timeout_ends_only_own_worker_and_keeps_partial_evidence(monkeypatch):
    line = {"section": "process", "data": {"pid": 24704, "name": "wsl.exe"}}
    workers = fake_worker(monkeypatch, timeouts=1, output=(json.dumps(line) + "\n").encode())
    result = module.collect()
    assert len(workers) == 1
    assert workers[0].killed
    assert workers[0].waits == [15, 2]
    assert result["metadata_worker_pid"] == 12345
    assert result["records"] == [line]
    assert result["deadline_exceeded"]
    assert result["wsl_clients_started"] == 0
    assert result["current_linux_health"] == "not_tested"
    assert not result["recovery_executed"]


def test_cleanup_wait_also_has_a_deadline(monkeypatch):
    workers = fake_worker(monkeypatch, timeouts=2)
    result = module.collect()
    assert workers[0].waits == [15, 2]
    assert result["metadata_worker_exit_unconfirmed"]


def test_partial_line_and_oversized_output_do_not_claim_completion(monkeypatch):
    fake_worker(monkeypatch, output=b'{"section":')
    assert module.collect()["incomplete_output_line"]
    monkeypatch.setattr(module, "MAX_OUTPUT_BYTES", 8)
    result = module.collect()
    assert result["output_limit_exceeded"]
    assert not result["records"]


def test_completed_metadata_is_not_linux_validation(monkeypatch):
    workers = fake_worker(monkeypatch, output=b'{"section":"completed","data":true}\n')
    result = module.collect()
    assert not workers[0].killed
    assert workers[0].waits == [15]
    assert workers[0].command[0].endswith("powershell.exe")
    assert workers[0].command[-2] == "-EncodedCommand"
    assert result["current_linux_health"] == "not_tested"
    assert not result["deadline_exceeded"]
