"""Loopback-only browser test server. Synthetic owner; no GitHub/model credentials."""

import tempfile
from pathlib import Path

import uvicorn

from repopilot.api import create_app
from repopilot.owner import OwnerConfig
from repopilot.owner_auth import password_hash

if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="repopilot-browser-") as folder:
        app = create_app(
            workspace=Path(folder),
            owner_config=OwnerConfig(
                mode="owner",
                origin="http://127.0.0.1:3011",
                secure=False,
                password=password_hash("browser-test-password-only"),
            ),
        )
        uvicorn.run(app, host="127.0.0.1", port=8011)
