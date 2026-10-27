import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from repopilot.fixtures import CATALOG
from repopilot.models import Check
from repopilot.policy import PolicyError, redact
from repopilot.workspace import assert_snapshot, clean_environment


class Runner:
    """Bounded subprocess for exact audited fixtures, NOT an untrusted-code sandbox."""

    def __init__(self, timeout: float = 20, output_limit: int = 65536):
        self.timeout = timeout
        self.output_limit = output_limit

    def run(
        self,
        root: Path,
        expected: dict[str, str],
        name: str,
        cancelled: Callable[[], bool] = lambda: False,
        kind: str = "pytest",
    ) -> Check:
        approved = [state for f in CATALOG.values() for state in (f.files, {**f.files, **f.edits})]
        if expected not in approved:
            raise PolicyError("untrusted_snapshot_execution_disabled")
        assert_snapshot(root, expected)
        command = [
            sys.executable,
            "-I",
            "-B",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "-c",
            str(Path(__file__).with_name("pytest.ini")),
            "--noconftest",
            "--rootdir",
            str(root),
            "--confcutdir",
            str(root),
            "test_app.py",
        ]
        if kind == "lint":
            command = [
                sys.executable,
                "-I",
                "-B",
                "-m",
                "ruff",
                "check",
                "--isolated",
                "--no-cache",
                "--select",
                "E,F,I",
                "--line-length",
                "100",
                "app.py",
                "test_app.py",
            ]
        elif kind == "format":
            command = [
                sys.executable,
                "-I",
                "-B",
                "-m",
                "ruff",
                "format",
                "--isolated",
                "--no-cache",
                "--line-length",
                "100",
                "--check",
                "app.py",
                "test_app.py",
            ]
        elif kind != "pytest":
            raise PolicyError("command_not_allowed")
        started = time.monotonic()
        timed_out = False
        was_cancelled = False
        limited = False
        with tempfile.TemporaryFile() as output:
            process = subprocess.Popen(
                command,
                cwd=root,
                env=clean_environment(),
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
            while process.poll() is None:
                was_cancelled = cancelled()
                timed_out = time.monotonic() - started > self.timeout
                limited = os.fstat(output.fileno()).st_size > self.output_limit
                if was_cancelled or timed_out or limited:
                    process.kill()
                    break
                time.sleep(0.02)
            code = process.wait(timeout=5)
            limited = limited or os.fstat(output.fileno()).st_size > self.output_limit
            output.seek(0)
            text = output.read(self.output_limit).decode("utf-8", errors="replace")
        if limited:
            text += "\n[output limit exceeded]"
            code = 125
        text = text.replace(str(root), "<workspace>")
        result = Check(
            name=name,
            command=[
                "python",
                *[
                    part.replace(str(root), "<workspace>").replace(
                        str(Path(__file__).parent), "<engine>"
                    )
                    for part in command[1:]
                ],
            ],
            exit_code=code,
            output=redact(text),
            duration_seconds=round(time.monotonic() - started, 3),
            timed_out=timed_out,
            cancelled=was_cancelled,
        )
        assert_snapshot(root, expected)
        return result


def command_policy(command: list[str]) -> None:
    # The public API never accepts commands. This guard documents the only named check.
    if command != ["pytest"]:
        raise PolicyError("command_not_allowed")
