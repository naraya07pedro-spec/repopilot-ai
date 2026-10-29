"""Run additive migrations against the configured database; never drop data."""

import os

from repopilot.migrations import migrate
from repopilot.store import Store

store = Store(
    os.environ["DATABASE_URL"],
    schema=os.environ.get("REPOPILOT_DATABASE_SCHEMA") or None,
    production=os.environ.get("REPOPILOT_ENV") == "production",
)
migrate(store.engine)
store.engine.dispose()
print("Schema version 2 applied; existing data preserved.")
