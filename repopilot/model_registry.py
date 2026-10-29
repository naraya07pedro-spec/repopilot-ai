"""Owner-configured model allowlist; credentials are never serialized."""

import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.engine import Engine

from repopilot.model_adapters import KEYS, ModelAdapter, ModelProfile
from repopilot.policy import PolicyError
from repopilot.private_planner import BudgetedPlanner


def load_profiles(path: str) -> tuple[ModelProfile, ...]:
    if not path:
        return ()
    raw = Path(path).read_bytes()
    if len(raw) > 32000:
        raise ValueError("model_profile_file_limit")
    data = json.loads(raw)
    if not isinstance(data, list) or len(data) > 20:
        raise ValueError("model_profile_count")
    profiles = tuple(ModelProfile.model_validate(item) for item in data)
    if len({p.id for p in profiles}) != len(profiles):
        raise ValueError("duplicate_model_profile")
    return profiles


class ModelRegistry:
    def __init__(
        self,
        client: httpx.Client,
        engine: Engine,
        profiles: tuple[ModelProfile, ...],
        daily_micro: int,
        run_micro: int,
        paid_enabled: bool,
    ):
        self.client, self.profiles = client, profiles
        self.planners: dict[str, BudgetedPlanner] = {}
        self.reasons: dict[str, str] = {}
        for profile in profiles:
            key = os.environ.get(KEYS[profile.provider], "") if profile.paid else ""
            reason = ""
            if profile.paid and not key:
                reason = "server_credentials_missing"
            elif profile.paid and (not paid_enabled or daily_micro <= 0 or run_micro <= 0):
                reason = "paid_calls_disabled_or_budget_missing"
            self.reasons[profile.id] = reason
            if not reason:
                self.planners[profile.id] = BudgetedPlanner(
                    client,
                    engine,
                    key,
                    profile.model,
                    daily_micro,
                    run_micro,
                    Decimal(str(profile.input_rate)),
                    Decimal(str(profile.output_rate)),
                    profile,
                )

    def catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "id": p.id,
                "provider": p.provider,
                "model": p.model,
                "paid": p.paid,
                "context_tokens": p.context_tokens,
                "output_tokens": p.output_tokens,
                "structured_output": p.structured_output,
                "available": p.id in self.planners,
                "reason": self.reasons[p.id],
                "validation": "configured capability; endpoint not yet verified",
            }
            for p in self.profiles
        ]

    def discover(self, profile_id: str) -> dict[str, Any]:
        profile = next((p for p in self.profiles if p.id == profile_id), None)
        if profile is None:
            raise PolicyError("model_profile_not_allowed")
        key = os.environ.get(KEYS[profile.provider], "") if profile.paid else ""
        if profile.paid and not key:
            raise PolicyError("server_credentials_missing")
        try:
            names = ModelAdapter(profile, key).discover(self.client)
            return {
                "profile": profile_id,
                "model": profile.model,
                "discovered": profile.model in names,
                "capabilities": "operator-configured; discovery alone does not validate generation",
            }
        except (KeyError, IndexError, TypeError, ValueError):
            raise PolicyError("provider_discovery_invalid") from None
