"""Extract bounded crash metadata and optional exact public exception signatures."""

import argparse
import json
import os
import re
import struct
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO

MAX_NOTES = 1024 * 1024
MAX_HEADERS = 256
EXCEPTION = re.compile(
    rb"Broken pipe @C:/__w/[0-9]+/s/src/shared/inc[\\/]+SocketChannel\.h:"
    rb"[0-9]+ \([A-Za-z0-9_:]+\)"
)


def note_metadata(data: bytes) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    offset = 0
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("truncated_note")
        namesz, descsz, kind = struct.unpack_from("<III", data, offset)
        offset += 12
        if namesz > 4096 or descsz > MAX_NOTES:
            raise ValueError("note_limit")
        name_end = offset + namesz
        desc_start = offset + ((namesz + 3) & ~3)
        desc_end = desc_start + descsz
        next_offset = desc_start + ((descsz + 3) & ~3)
        if next_offset > len(data):
            raise ValueError("truncated_note")
        name = data[offset:name_end].rstrip(b"\0")
        desc = data[desc_start:desc_end]
        offset = next_offset
        if name != b"CORE":
            continue
        if kind == 1 and len(desc) >= 48:
            result.append(
                {
                    "type": "NT_PRSTATUS",
                    "signal": struct.unpack_from("<h", desc, 12)[0],
                    "pid": struct.unpack_from("<i", desc, 32)[0],
                }
            )
        elif kind == 3 and len(desc) >= 56:
            result.append(
                {
                    "type": "NT_PRPSINFO",
                    "executable": desc[40:56].split(b"\0")[0].decode("ascii", errors="replace"),
                    "pid": struct.unpack_from("<i", desc, 24)[0],
                }
            )
        elif kind == 0x53494749 and len(desc) >= 12:
            result.append(
                {
                    "type": "NT_SIGINFO",
                    "signal": struct.unpack_from("<i", desc, 0)[0],
                    "code": struct.unpack_from("<i", desc, 8)[0],
                }
            )
    return result


def inspect_stream(stream: BinaryIO, file_size: int) -> dict[str, Any]:
    header = stream.read(64)
    if len(header) != 64 or header[:6] != b"\x7fELF\x02\x01":
        return {"elf_core": False, "notes": []}
    values = struct.unpack("<16sHHIQQQIHHHHHH", header)
    if values[1] != 4 or values[2] != 62:
        return {"elf_core": False, "notes": []}
    phoff, phsize, phnum = values[5], values[9], values[10]
    if not 56 <= phsize <= 1024 or phnum > MAX_HEADERS:
        raise ValueError("header_limit")
    if phoff < 64 or phoff + phsize * phnum > file_size:
        raise ValueError("header_bounds")
    notes: list[dict[str, Any]] = []
    read_bytes = 0
    for index in range(phnum):
        stream.seek(phoff + index * phsize)
        fields = struct.unpack("<IIQQQQQQ", stream.read(56))
        if fields[0] != 4:  # Never read PT_LOAD process-memory segments.
            continue
        location, length = fields[2], fields[5]
        read_bytes += length
        if read_bytes > MAX_NOTES or location + length > file_size:
            raise ValueError("note_bounds")
        stream.seek(location)
        notes.extend(note_metadata(stream.read(length)))
    return {"elf_core": True, "notes": notes}


def inspect_file(path: Path, known_exception: bool = False) -> dict[str, Any]:
    stat = path.stat()
    result: dict[str, Any] = {
        "file": path.name,
        "bytes": stat.st_size,
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    }
    try:
        with path.open("rb") as stream:
            result.update(inspect_stream(stream, stat.st_size))
            if known_exception:
                if stat.st_size > MAX_NOTES:
                    result["exception_scan"] = "skipped_size_limit"
                else:
                    stream.seek(0)
                    result["known_exception_matches"] = sorted(
                        {
                            value.decode("ascii")
                            for value in EXCEPTION.findall(stream.read(MAX_NOTES))
                        }
                    )
    except (OSError, ValueError, struct.error):
        result.update(elf_core=False, notes=[], error="unreadable_or_malformed_core")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    default = Path(os.environ.get("LOCALAPPDATA", ".")) / "Temp" / "wsl-crashes"
    parser.add_argument("--directory", type=Path, default=default)
    parser.add_argument(
        "--known-exception",
        action="store_true",
        help="Scan at most 1 MiB per core for an exact public broken-pipe/source-path signature",
    )
    args = parser.parse_args()
    paths = sorted(
        args.directory.glob("wsl-crash-*.dmp"), key=lambda path: path.stat().st_mtime, reverse=True
    )[:32]
    print(
        json.dumps(
            {
                "metadata_only": not args.known_exception,
                "raw_memory_printed_or_copied": False,
                "crashes": [inspect_file(p, args.known_exception) for p in paths],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
