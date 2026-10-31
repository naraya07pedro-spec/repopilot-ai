"""Bounded paid-provider adapter with durable conservative spend reservations."""

import json
import math
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from repopilot.migrations import budgets
from repopilot.model_adapters import ModelAdapter, ModelProfile, bounded_json
from repopilot.models import Plan
from repopilot.policy import PolicyError


class BudgetedPlanner:
    def __init__(
        self,
        client: httpx.Client,
        engine: Engine,
        api_key: str,
        model: str,
        daily_micro: int,
        run_micro: int,
        input_rate: Decimal,
        output_rate: Decimal,
        profile: ModelProfile | None = None,
    ):
        self.client, self.engine, self.api_key, self.model = client, engine, api_key, model
        self.daily_micro, self.run_micro = daily_micro, run_micro
        self.input_rate, self.output_rate = input_rate, output_rate
        self.profile = profile or ModelProfile(
            id="default",
            provider="openai",
            model=model,
            structured_output="json_schema",
            context_tokens=65536,
            input_rate=float(input_rate),
            output_rate=float(output_rate),
        )
        self.adapter = ModelAdapter(self.profile, api_key)
        if self.profile.paid and (
            not api_key
            or daily_micro <= 0
            or run_micro <= 0
            or not input_rate.is_finite()
            or not output_rate.is_finite()
            or input_rate <= 0
            or output_rate <= 0
        ):
            raise PolicyError("provider_budget_not_configured")

    def reserve(self, amount: int) -> None:
        day = datetime.now(UTC).date().isoformat()
        try:
            with self.engine.begin() as conn:
                conn.execute(budgets.insert().values(day=day, reserved=0))
        except IntegrityError:
            pass
        with self.engine.begin() as conn:
            result = conn.execute(
                update(budgets)
                .where(budgets.c.day == day, budgets.c.reserved + amount <= self.daily_micro)
                .values(reserved=budgets.c.reserved + amount)
            )
            if result.rowcount != 1:
                raise PolicyError("daily_budget_exhausted")

    def binding(self, run_micro: int | None = None) -> dict[str, Any]:
        return {
            "profile": self.profile.model_dump(),
            "run_micro": self.run_micro if run_micro is None else run_micro,
            "daily_micro": self.daily_micro,
        }

    def plan(
        self, snapshot: dict[str, Any], run_micro: int | None = None
    ) -> tuple[Plan, dict[str, Any]]:
        url, payload = self.adapter.request(snapshot)
        encoded = json.dumps(payload).encode()
        input_bound = len(encoded) + 4096
        output_bound = self.profile.output_tokens
        if (
            len(encoded) > self.profile.context_bytes
            or input_bound + output_bound > self.profile.context_tokens
        ):
            raise PolicyError("model_context_limit")
        reservation = (
            math.ceil(
                Decimal(input_bound) * self.input_rate + Decimal(output_bound) * self.output_rate
            )
            if self.profile.paid
            else 0
        )
        limit = self.run_micro if run_micro is None else min(run_micro, self.run_micro)
        if self.profile.paid and reservation * 2 > limit:
            raise PolicyError("run_budget_exhausted")
        for attempt in range(2):
            if reservation:
                self.reserve(reservation)
            try:
                data = bounded_json(self.client, "POST", url, self.adapter.headers(), payload)
                plan, prompt, completion = self.adapter.parse(data)
                if (
                    type(prompt) is not int
                    or type(completion) is not int
                    or not 0 <= prompt <= input_bound
                    or not 0 <= completion <= output_bound
                ):
                    raise PolicyError("provider_usage_invalid")
                return plan, {
                    "provider": self.profile.provider,
                    "model": self.model,
                    "execution_kind": "real_model",
                    "prompt_tokens": prompt,
                    "completion_tokens": completion,
                    "estimated_cost_micro_usd": math.ceil(
                        Decimal(prompt) * self.input_rate + Decimal(completion) * self.output_rate
                    )
                    if self.profile.paid
                    else 0,
                    "reserved_micro_usd": reservation * (attempt + 1),
                    "attempts": attempt + 1,
                    "pricing_source": "operator-configured rates; not a provider invoice"
                    if self.profile.paid
                    else "local endpoint; no external API billing",
                }
            except PolicyError as exc:
                if (
                    str(exc) in {"provider_http_429", "provider_http_502", "provider_http_503"}
                    and attempt == 0
                ):
                    time.sleep(0.2)
                    continue
                raise
            except (KeyError, IndexError, TypeError, ValueError):
                raise PolicyError("provider_invalid_output") from None
        raise PolicyError("provider_retry_exhausted")

    def reserved_today(self) -> int:
        with self.engine.connect() as conn:
            result = conn.execute(
                select(budgets.c.reserved).where(
                    budgets.c.day == datetime.now(UTC).date().isoformat()
                )
            ).scalar_one_or_none()
            return int(result or 0)
