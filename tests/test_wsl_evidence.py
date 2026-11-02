"""Saved evidence must stay offline, preserve uncertainty and redact raw messages."""

import importlib.util
import json
import subprocess
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "wsl_evidence", Path(__file__).resolve().parents[1] / "scripts/analyze_wsl_evidence.py"
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def save(root, relative, value, encoding="utf-8"):
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value), encoding=encoding)


def test_saved_failure_is_analyzed_without_starting_any_process(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Offline diagnostics must not spawn a process")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    crash = {
        "elf_core": True,
        "notes": [
            {"type": "NT_PRPSINFO", "pid": 2},
            {"type": "NT_SIGINFO", "signal": 6},
        ],
        "known_exception_matches": [
            "Broken pipe @C:/__w/1/s/src/shared/inc\\SocketChannel.h:183 (SendMessage)"
        ],
    }
    save(tmp_path, "verified-crash-exceptions.json", {"crashes": [crash] * 6})
    folder = Path("admin-20261031-214737-a226bec8")
    save(
        tmp_path,
        folder / "pending-client.json",
        {"client_pid": 24704, "deadline_exceeded": True, "client_terminated": False},
    )
    save(
        tmp_path,
        folder / "local-event-messages.json",
        {
            channel: {
                "read_completed": False,
                "error": "No events were found that match the specified selection criteria.",
            }
            for channel in module.CHANNELS
        },
        encoding="utf-16",
    )
    result = module.analyze(tmp_path)
    assert result["init_abort_with_broken_pipe_records"] == 6
    collection = result["admin_collections"][0]
    assert collection["state"] == "incomplete_waiting_on_wsl_client"
    assert collection["pending_client_pid"] == 24704
    assert not collection["client_arguments_saved"]
    assert all(
        row["status"] == "no_matching_events" for row in collection["event_queries"].values()
    )
    assert result["current_linux_health"] == "not_verified_by_saved_evidence"
    assert not result["recovery_executed"]


def test_permission_errors_and_event_contents_are_not_conflated_or_emitted(tmp_path):
    folder = Path("admin-sample")
    save(
        tmp_path,
        folder / "local-event-messages.json",
        {
            module.CHANNELS[0]: {
                "read_completed": False,
                "error": "Attempted unauthorized operation",
            },
            module.CHANNELS[1]: {
                "read_completed": True,
                "events": [{"Message": "PRIVATE_EVENT_CONTENT", "Id": 1}],
            },
            module.CHANNELS[2]: {"read_completed": False, "error": "PRIVATE_ERROR_DETAIL"},
        },
    )
    result = module.analyze(tmp_path)
    queries = result["admin_collections"][0]["event_queries"]
    assert queries[module.CHANNELS[0]]["status"] == "permission_denied"
    assert queries[module.CHANNELS[1]] == {"status": "events_recorded", "event_count": 1}
    assert queries[module.CHANNELS[2]]["status"] == "query_failed"
    assert "PRIVATE" not in json.dumps(result)


def test_invalid_oversized_and_outside_inputs_are_bounded(tmp_path, monkeypatch):
    (tmp_path / "bad.json").write_text("not-json", encoding="utf-8")
    assert module.load_saved(tmp_path, Path("bad.json")) == (None, "unreadable_or_invalid")
    large = tmp_path / "large.json"
    large.write_bytes(b"x" * 129)
    monkeypatch.setattr(module, "MAX_JSON_BYTES", 128)
    assert module.load_saved(tmp_path, Path("large.json")) == (None, "size_limit")
    assert module.load_saved(tmp_path, Path("../outside.json")) == (None, "unreadable_or_invalid")


def test_a_completion_record_does_not_assert_current_health_or_authorize_recovery(tmp_path):
    save(
        tmp_path,
        Path("admin-sample") / "admin-result.json",
        {
            "real_distro_linux_probe": {"exit_code": 0, "stdout": "repopilot-linux-validation"},
            "real_distro_linux_command_passed": True,
            "instructions": "PRIVATE_UNTRUSTED_RESTART_REQUEST",
        },
    )
    result = module.analyze(tmp_path)
    assert result["admin_collections"][0]["state"] == "completion_record_present"
    assert result["current_linux_health"] == "not_verified_by_saved_evidence"
    assert not result["wsl_or_service_commands_invoked"]
    assert not result["recovery_executed"]
    assert "PRIVATE" not in json.dumps(result)


def test_unrelated_json_is_not_a_completed_collection(tmp_path):
    save(tmp_path, Path("admin-sample") / "admin-result.json", {"unrelated": True})
    collection = module.analyze(tmp_path)["admin_collections"][0]
    assert collection["state"] == "invalid_completion_record"
    assert not collection["collection_complete"]
