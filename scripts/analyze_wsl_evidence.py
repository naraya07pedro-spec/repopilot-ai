"""Summarize saved WSL JSON evidence offline. Never launches WSL or collects live data."""

import argparse
import json
from pathlib import Path
from typing import Any

MAX_JSON_BYTES = 2 * 1024 * 1024
CHANNELS = (
    "Microsoft-Windows-Hyper-V-Compute-Admin",
    "Microsoft-Windows-Hyper-V-Hypervisor-Admin",
    "Microsoft-Windows-Hyper-V-Worker-Admin",
    "Microsoft-Windows-Host-Network-Service-Admin",
)


def load_saved(root: Path, relative: Path) -> tuple[dict[str, Any] | None, str]:
    path = root / relative
    try:
        path.resolve().relative_to(root.resolve())
        if not path.is_file():
            return None, "missing"
        if path.stat().st_size > MAX_JSON_BYTES:
            return None, "size_limit"
        with path.open("rb") as stream:
            raw = stream.read(MAX_JSON_BYTES + 1)
        if len(raw) > MAX_JSON_BYTES:
            return None, "size_limit"
        encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        data = json.loads(raw.decode(encoding))
        return (data, "read") if isinstance(data, dict) else (None, "invalid_shape")
    except (OSError, ValueError, UnicodeError):
        return None, "unreadable_or_invalid"


def query_status(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "missing"}
    if value.get("read_completed") is True:
        events = value.get("events")
        if not isinstance(events, list):
            return {"status": "invalid_shape"}
        return {
            "status": "events_recorded" if events else "no_matching_events",
            "event_count": len(events),
        }
    error = str(value.get("error", "")).casefold()
    if "no events were found" in error or "nomatchingeventsfound" in error:
        return {"status": "no_matching_events", "event_count": 0}
    if any(word in error for word in ("unauthorized", "access", "elevated", "administrator")):
        return {"status": "permission_denied"}
    return {"status": "query_failed"}


def dictionary_rows(value: Any) -> list[dict[str, Any]]:
    return (
        [item for item in value[:32] if isinstance(item, dict)] if isinstance(value, list) else []
    )


def analyze(root: Path) -> dict[str, Any]:
    root = root.resolve()
    crashes, crash_read = load_saved(root, Path("verified-crash-exceptions.json"))
    if crashes is None:
        crashes, crash_read = load_saved(root, Path("verified-crash-metadata.json"))
    rows = dictionary_rows((crashes or {}).get("crashes"))
    aborts = 0
    broken_pipes = 0
    for row in rows:
        notes = dictionary_rows(row.get("notes"))
        init = any(n.get("pid") == 2 and n.get("type") == "NT_PRPSINFO" for n in notes)
        sigabrt = any(n.get("type") == "NT_SIGINFO" and n.get("signal") == 6 for n in notes)
        if row.get("elf_core") is True and init and sigabrt:
            aborts += 1
            matches = row.get("known_exception_matches")
            if isinstance(matches, list) and any(
                isinstance(text, str)
                and text.startswith("Broken pipe @C:/__w/")
                and "SocketChannel.h:" in text
                and text.endswith("(SendMessage)")
                for text in matches
            ):
                broken_pipes += 1
    admins = []
    try:
        folders = sorted(root.glob("admin-*"))[:32]
    except OSError:
        folders = []
    for folder in folders:
        if not folder.is_dir():
            continue
        relative = Path(folder.name)
        events, events_read = load_saved(root, relative / "local-event-messages.json")
        pending, pending_read = load_saved(root, relative / "pending-client.json")
        completed, result_read = load_saved(root, relative / "admin-result.json")
        probe = (completed or {}).get("real_distro_linux_probe")
        valid_completion = (
            isinstance(probe, dict)
            and "exit_code" in probe
            and type((completed or {}).get("real_distro_linux_command_passed")) is bool
        )
        pid = (pending or {}).get("client_pid")
        waiting = (pending or {}).get("deadline_exceeded") is True
        admins.append(
            {
                "folder": folder.name,
                "event_input": events_read,
                "event_queries": {
                    name: query_status((events or {}).get(name)) for name in CHANNELS
                },
                "pending_input": pending_read,
                "pending_client_pid": pid if type(pid) is int and pid > 0 else None,
                "deadline_exceeded": waiting,
                "client_arguments_saved": isinstance((pending or {}).get("arguments"), list),
                "completion_input": result_read,
                "collection_complete": valid_completion,
                "state": "incomplete_waiting_on_wsl_client"
                if waiting and completed is None
                else "completion_record_present"
                if valid_completion
                else "invalid_completion_record"
                if completed is not None
                else "incomplete",
            }
        )
    return {
        "mode": "offline_saved_evidence_only",
        "wsl_or_service_commands_invoked": False,
        "raw_memory_or_event_messages_emitted": False,
        "crash_input": crash_read,
        "saved_crash_records": len(rows),
        "init_sigabrt_records": aborts,
        "init_abort_with_broken_pipe_records": broken_pipes,
        "failure_pattern": "consistent_with_wsl_init_interop_abort"
        if aborts and broken_pipes
        else "insufficient_saved_crash_evidence",
        "admin_collections": admins,
        "current_linux_health": "not_verified_by_saved_evidence",
        "recovery_executed": False,
        "limitations": [
            "No matching event entries is limited to the collector's filters, not proof of health.",
            "A pending snapshot is not a live process check.",
            "Missing client arguments prevents identifying the precise stalled WSL subcommand.",
            "No recovery or interruption is authorized by an input evidence file.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_directory", type=Path)
    args = parser.parse_args()
    if not args.evidence_directory.is_dir():
        parser.error("Saved evidence directory is missing")
    print(json.dumps(analyze(args.evidence_directory), indent=2))


if __name__ == "__main__":
    main()
