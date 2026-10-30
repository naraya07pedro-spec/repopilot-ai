"""Read-only, secret-free local configuration diagnostics. Makes no external calls."""

import json
import os
import shutil
import sys
from typing import Any

from repopilot.owner import OwnerConfig


def report() -> dict[str, Any]:
    result: dict[str, Any] = {
        "python_supported": sys.version_info >= (3, 12),
        "node_available": shutil.which("node") is not None,
        "git_available": shutil.which("git") is not None,
        "owner_configuration_valid": False,
        "github_app_configured": False,
        "model_profiles": 0,
        "execution_enabled": False,
        "execution_reason": "No verified runtime integration is activated in this build",
        "live_integrations_validated": False,
        "paid_calls_authorized": False,
    }
    try:
        cfg = OwnerConfig.from_env()
        cfg.validate()
        result.update(
            owner_configuration_valid=cfg.mode == "owner" and bool(cfg.password),
            github_app_configured=bool(
                cfg.app_id and cfg.installation and cfg.app_key and cfg.repositories
            ),
            model_profiles=len(cfg.profiles),
            paid_calls_authorized=cfg.paid_enabled and cfg.run_micro > 0 and cfg.daily_micro > 0,
        )
    except (ValueError, TypeError, OSError, AttributeError):
        result["configuration_error"] = (
            "Invalid or unreadable owner configuration; inspect local setup"
        )
    result["provider_credentials_present"] = {
        name: bool(os.environ.get(name))
        for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")
    }
    result["next_steps"] = [
        "Configure owner password hash and matching loopback origin",
        "Configure installation-scoped GitHub App and server-approved source root",
        "Configure a model profile; keep paid execution denied without explicit authorization",
        "Keep execution closed until a reviewed isolated Linux runtime is supplied and verified",
    ]
    return result


if __name__ == "__main__":
    print(json.dumps(report(), indent=2))
