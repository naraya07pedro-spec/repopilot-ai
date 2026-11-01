"""OS-released single-process lease. A stale filename never blocks restart recovery."""

import os
from importlib import import_module
from pathlib import Path
from typing import BinaryIO

from repopilot.policy import PolicyError


class WorkspaceLease:
    def __init__(self, directory: Path):
        path = directory / "workspace.lock"
        if any(
            p.is_symlink() or p.is_junction() for p in (path.absolute(), *path.absolute().parents)
        ):
            raise PolicyError("workspace_lock_reparse_point")
        self.stream: BinaryIO = path.open("a+b")
        self.stream.seek(0)
        if path.stat().st_size == 0:
            self.stream.write(b"0")
            self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == "nt":
                windows_lock = import_module("msvcrt")
                windows_lock.locking(self.stream.fileno(), windows_lock.LK_NBLCK, 1)
            else:
                linux_lock = import_module("fcntl")
                linux_lock.flock(self.stream.fileno(), linux_lock.LOCK_EX | linux_lock.LOCK_NB)
        except OSError:
            self.stream.close()
            raise PolicyError("workspace_already_running_close_its_own_launcher_first") from None

    def close(self) -> None:
        self.stream.close()  # The OS releases the lease on close or process exit.
