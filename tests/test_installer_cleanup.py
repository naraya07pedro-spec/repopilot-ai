"""A taskkill exit race may be harmless; failed live cleanup must remain fail-closed."""

import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts import smoke_installed_local as smoke


def test_exited_owned_launcher_does_not_kill_anything(monkeypatch):
    run = Mock()
    monkeypatch.setattr(smoke.subprocess, "run", run)
    process = SimpleNamespace(poll=lambda: 0, wait=Mock(return_value=0))
    smoke.stop_owned_launcher(process, windows=True)
    run.assert_not_called()


def test_taskkill_race_requires_confirmed_exit_and_targets_only_owned_pid(monkeypatch):
    monkeypatch.setenv("SystemRoot", "C:/Windows")
    run = Mock(return_value=SimpleNamespace(returncode=128))
    monkeypatch.setattr(smoke.subprocess, "run", run)
    process = SimpleNamespace(pid=12345, poll=lambda: None, wait=Mock(return_value=0))
    smoke.stop_owned_launcher(process, windows=True)
    command = run.call_args.args[0]
    assert command[1:] == ["/PID", "12345", "/T", "/F"]
    assert process.wait.call_args_list[0].kwargs == {"timeout": 3}
    assert run.call_count == 1


def test_failed_live_cleanup_does_not_escalate_to_other_processes(monkeypatch):
    monkeypatch.setenv("SystemRoot", "C:/Windows")
    run = Mock(return_value=SimpleNamespace(returncode=128))
    monkeypatch.setattr(smoke.subprocess, "run", run)
    process = SimpleNamespace(
        pid=12345,
        poll=lambda: None,
        wait=Mock(side_effect=subprocess.TimeoutExpired("test-owned-launcher", 3)),
        kill=Mock(),
    )
    with pytest.raises(RuntimeError, match="no_broader_cleanup_attempted"):
        smoke.stop_owned_launcher(process, windows=True)
    process.kill.assert_not_called()
    assert run.call_count == 1
