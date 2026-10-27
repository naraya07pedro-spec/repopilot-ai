from pathlib import Path

import pytest

from repopilot.engine import Engine
from repopilot.store import Store


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(f"sqlite:///{tmp_path / 'test.db'}")


@pytest.fixture
def engine(store: Store, tmp_path: Path) -> Engine:
    return Engine(store, tmp_path / "spaces")
