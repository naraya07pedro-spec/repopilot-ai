"""Trusted image entrypoint. Runs only inside the sandbox, never on the controller."""

import json
import os
import re
import sys
from pathlib import Path

COMMANDS = {
    "pytest": [
        "python",
        "-I",
        "-B",
        "-m",
        "pytest",
        "-q",
        "--noconftest",
        "-p",
        "no:cacheprovider",
        ".",
    ],
    "lint": ["python", "-I", "-m", "ruff", "check", "--isolated", "--no-cache", "."],
    "format": ["python", "-I", "-m", "ruff", "format", "--isolated", "--no-cache", "--check", "."],
}


def main() -> None:
    if os.getuid() != 65532 or Path.cwd() != Path("/work"):
        raise SystemExit("invalid guest identity")
    raw = sys.stdin.buffer.read(256001)
    if len(raw) > 256000:
        raise SystemExit("source limit")
    files = json.loads(raw)
    if not isinstance(files, dict) or not 1 <= len(files) <= 32:
        raise SystemExit("source count")
    for name, content in files.items():
        if (
            not re.fullmatch(r"[A-Za-z0-9_/-]+\.py", name)
            or name.startswith("/")
            or any(p in {"", ".", ".."} for p in name.split("/"))
            or not isinstance(content, str)
        ):
            raise SystemExit("source path")
        target = Path("/work") / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="")
    command = COMMANDS[sys.argv[1]]
    os.execve(
        "/opt/tools/bin/python",
        command,
        {
            "PATH": "/opt/tools/bin:/usr/bin:/bin",
            "HOME": "/tmp",
            "TMPDIR": "/tmp",
            "LANG": "C.UTF-8",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )


if __name__ == "__main__":
    main()
