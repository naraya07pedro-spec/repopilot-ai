import os
import subprocess
from pathlib import Path

from repopilot.policy import PolicyError, safe_path


def clean_environment() -> dict[str, str]:
    keep = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR"}
    env = {k: v for k, v in os.environ.items() if k.upper() in keep}
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return env


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=" + os.devnull,
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.autocrlf=false",
            *args,
        ],
        cwd=root,
        env=clean_environment(),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode:
        raise PolicyError("git_operation_failed")
    return result.stdout.strip()


def initialize(root: Path, files: dict[str, str], branch: str) -> str:
    root.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        safe_path(root, name).write_text(content, encoding="utf-8", newline="\n")
    git(root, "init", "--initial-branch=main", "--template=")
    git(root, "config", "user.name", "RepoPilot Fixture")
    git(root, "config", "user.email", "fixture@repopilot.invalid")
    git(root, "add", "--", *files.keys())
    git(root, "commit", "-m", "Baseline audited fixture")
    baseline = git(root, "rev-parse", "HEAD")
    git(root, "switch", "-c", branch)
    return baseline


def inspect(root: Path, max_files: int = 64, max_bytes: int = 48000) -> dict[str, object]:
    names = git(root, "ls-files").splitlines()
    if len(names) > max_files:
        raise PolicyError("repository_file_limit")
    result: dict[str, str] = {}
    size = 0
    for name in names:
        path = safe_path(root, name)
        size += path.stat().st_size
        if size > max_bytes:
            raise PolicyError("repository_context_limit")
        result[name] = path.read_text(encoding="utf-8")
    return {
        "files": result,
        "bytes": size,
        "language": "Python",
        "framework": "pytest",
        "dependencies": ["pytest"],
        "baseline": git(root, "rev-parse", "HEAD"),
    }


def assert_snapshot(root: Path, expected: dict[str, str]) -> None:
    actual = {
        p.relative_to(root).as_posix(): p
        for p in root.rglob("*")
        if ".git" not in p.relative_to(root).parts and p.is_file()
    }
    if set(actual) != set(expected):
        raise PolicyError("unexpected_workspace_files")
    for name, content in expected.items():
        path = safe_path(root, name)
        if path.read_text(encoding="utf-8") != content:
            raise PolicyError("workspace_bytes_changed")


def apply(root: Path, edits: dict[str, str]) -> None:
    for name, content in edits.items():
        safe_path(root, name).write_text(content, encoding="utf-8", newline="\n")
