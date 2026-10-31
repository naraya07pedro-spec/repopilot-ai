"""Crash diagnostics must expose metadata without reading process-memory segments."""

import importlib.util
import io
import json
import struct
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "wsl_crash_notes", Path(__file__).resolve().parents[1] / "scripts/inspect_wsl_crash_notes.py"
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def note(kind, desc):
    return (
        struct.pack("<III", 5, len(desc), kind) + b"CORE\0\0\0\0" + desc + b"\0" * (-len(desc) % 4)
    )


def core(notes, memory=b"PRIVATE_PROCESS_MEMORY"):
    ident = b"\x7fELF\x02\x01" + b"\0" * 10
    header = struct.pack("<16sHHIQQQIHHHHHH", ident, 4, 62, 1, 0, 64, 0, 0, 64, 56, 2, 0, 0, 0)
    start = 64 + 112
    ph_notes = struct.pack("<IIQQQQQQ", 4, 0, start, 0, 0, len(notes), len(notes), 4)
    ph_load = struct.pack("<IIQQQQQQ", 1, 0, start + len(notes), 0, 0, len(memory), len(memory), 4)
    return header + ph_notes + ph_load + notes + memory


def test_only_allowlisted_metadata_is_emitted():
    info = bytearray(136)
    struct.pack_into("<i", info, 24, 2)
    info[40:56] = b"init-systemd(Op\0\0"
    info[56:80] = b"PRIVATE_COMMAND_ARGUMENT"
    sig = struct.pack("<iii", 6, 0, -6)
    payload = core(note(3, info) + note(0x53494749, sig) + note(999, b"PRIVATE_NOTE"))
    result = module.inspect_stream(io.BytesIO(payload), len(payload))
    assert result == {
        "elf_core": True,
        "notes": [
            {"type": "NT_PRPSINFO", "executable": "init-systemd(Op", "pid": 2},
            {"type": "NT_SIGINFO", "signal": 6, "code": -6},
        ],
    }
    assert "PRIVATE" not in json.dumps(result)


def test_oversized_note_is_rejected_before_a_large_read():
    payload = bytearray(core(b""))
    struct.pack_into("<Q", payload, 64 + 32, 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="note_bounds"):
        module.inspect_stream(io.BytesIO(payload), len(payload))


def test_non_core_and_truncated_notes_do_not_expose_data():
    assert module.inspect_stream(io.BytesIO(b"PRIVATE_NOT_A_CORE"), 18) == {
        "elf_core": False,
        "notes": [],
    }
    payload = core(struct.pack("<III", 5, 4096, 3) + b"CORE\0\0\0\0")
    with pytest.raises(ValueError, match="truncated_note"):
        module.inspect_stream(io.BytesIO(payload), len(payload))


def test_opt_in_exception_scan_excludes_adjacent_private_bytes(tmp_path):
    exception = b"Broken pipe @C:/__w/1/s/src/shared/inc\\SocketChannel.h:183 (SendMessage)"
    path = tmp_path / "wsl-crash-123-2-_init-6.dmp"
    path.write_bytes(core(b"", b"PRIVATE_BEFORE" + exception + b"\0PRIVATE_AFTER"))
    default = module.inspect_file(path)
    assert "known_exception_matches" not in default
    result = module.inspect_file(path, known_exception=True)
    assert result["known_exception_matches"] == [exception.decode("ascii")]
    assert "PRIVATE" not in json.dumps(result)
