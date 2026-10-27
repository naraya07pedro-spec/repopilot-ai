import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


class PolicyError(ValueError):
    pass


SECRET = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"sk-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?i:authorization\s*[:=]\s*bearer\s+)\S+)"
)


def redact(value: str) -> str:
    return SECRET.sub("[REDACTED]", value)


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def safe_path(root: Path, name: str) -> Path:
    parts = PurePosixPath(name).parts
    if (
        not parts
        or "\\" in name
        or ":" in name
        or name.startswith("/")
        or any(p in {".", ".."} or p.startswith(".") or p.endswith((".", " ")) for p in parts)
        or any(
            p.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", "COM1", "LPT1"} for p in parts
        )
        or not re.fullmatch(r"[A-Za-z0-9_./-]+", name)
    ):
        raise PolicyError("unsafe_path")
    candidate = root.joinpath(*parts)
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise PolicyError("path_escape")
    if any(p.is_symlink() for p in [candidate, *candidate.parents] if p != root.parent):
        raise PolicyError("symlink_blocked")
    return candidate


def repository_name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", value):
        raise PolicyError("invalid_repository")
    if any(p in {".", ".."} for p in value.split("/")):
        raise PolicyError("invalid_repository")
    return value


def validate_edits(edits: dict[str, str], approved: dict[str, str]) -> None:
    if not edits or len(edits) > 4:
        raise PolicyError("edit_budget")
    for name, content in edits.items():
        safe_path(Path.cwd(), name)
        if SECRET.search(content):
            raise PolicyError("secret_detected")
        if name not in approved or content != approved[name]:
            raise PolicyError("untrusted_edit_execution_disabled")
