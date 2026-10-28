"""Durable private planning; arbitrary execution fails closed until a worker is validated."""

import json
import re
import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from repopilot.github_app import GitHubApp
from repopilot.migrations import private_runs
from repopilot.policy import SECRET, PolicyError, digest
from repopilot.private_planner import BudgetedPlanner
from repopilot.store import now


class PrivateService:
    def __init__(self, engine: Engine, github: GitHubApp | None, planner: BudgetedPlanner | None):
        self.engine, self.github, self.planner = engine, github, planner

    def get(self, identity: str) -> dict[str, Any]:
        with self.engine.connect() as conn:
            row = (
                conn.execute(select(private_runs).where(private_runs.c.id == identity))
                .mappings()
                .first()
            )
        if row is None:
            raise KeyError(identity)
        return {**json.loads(row["payload"]), "status": row["status"]}

    def history(self) -> list[dict[str, Any]]:
        with self.engine.connect() as conn:
            rows = (
                conn.execute(
                    select(private_runs).order_by(private_runs.c.created_at.desc()).limit(100)
                )
                .mappings()
                .all()
            )
        return sorted(
            ({**json.loads(r["payload"]), "status": r["status"]} for r in rows),
            key=lambda r: r["created_at"],
            reverse=True,
        )

    def create(self, repository: str, number: int, key: str) -> tuple[dict[str, Any], bool]:
        if not self.github or repository not in self.github.allowed:
            raise PolicyError("github_app_or_repository_not_configured")
        if not self.planner:
            raise PolicyError("model_credentials_or_budget_missing")
        request = {"repository": repository, "issue_number": number}
        fingerprint, identity = digest(request), uuid.uuid4().hex
        payload = {
            "id": identity,
            **request,
            "created_at": now(),
            "events": [{"at": now(), "name": "queued"}],
        }
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    private_runs.insert().values(
                        id=identity,
                        request_key=key,
                        fingerprint=fingerprint,
                        status="queued",
                        created_at=payload["created_at"],
                        payload=json.dumps(payload),
                    )
                )
            return self.get(identity), True
        except IntegrityError:
            with self.engine.connect() as conn:
                row = (
                    conn.execute(select(private_runs).where(private_runs.c.request_key == key))
                    .mappings()
                    .one()
                )
            if row["fingerprint"] != fingerprint:
                raise PolicyError("idempotency_conflict") from None
            return self.get(row["id"]), False

    def transition(
        self, identity: str, before: list[str], after: str, payload: dict[str, Any] | None = None
    ) -> bool:
        values: dict[str, Any] = {"status": after}
        if payload is not None:
            values["payload"] = json.dumps(payload)
        with self.engine.begin() as conn:
            result = conn.execute(
                update(private_runs)
                .where(private_runs.c.id == identity, private_runs.c.status.in_(before))
                .values(**values)
            )
            return result.rowcount == 1

    def prepare(self, identity: str) -> None:
        if not self.transition(identity, ["queued"], "planning"):
            return
        data = self.get(identity)
        try:
            if self.github is None or self.planner is None:
                raise PolicyError("provider_not_configured")
            snapshot = self.github.snapshot(data["repository"], data["issue_number"])
            if SECRET.search(json.dumps(snapshot)):
                raise PolicyError("context_secret_pattern")
            if self.get(identity)["status"] != "planning":
                return
            plan, usage = self.planner.plan(snapshot)
            paths = [edit.path for edit in plan.edits]
            if len(set(paths)) != len(paths):
                raise PolicyError("duplicate_edit")
            for edit in plan.edits:
                if not re.fullmatch(r"[A-Za-z0-9_/-]+\.(py|ts|tsx)", edit.path) or any(
                    part in {"", ".", ".."} or part.startswith(".") for part in edit.path.split("/")
                ):
                    raise PolicyError("private_edit_path")
                if edit.path not in snapshot["files"] and not re.fullmatch(
                    r"tests/test_[A-Za-z0-9_]+\.py", edit.path
                ):
                    raise PolicyError("private_edit_scope")
                if SECRET.search(edit.content):
                    raise PolicyError("edit_secret_pattern")
            data.update(
                snapshot=snapshot,
                plan=plan.model_dump(),
                usage=usage,
                approval_digest=digest({"snapshot": snapshot, "plan": plan.model_dump()}),
            )
            data["events"].append(
                {
                    "at": now(),
                    "name": "plan_ready",
                    "detail": (
                        "Real-model plan; execution requires a separately validated isolated worker"
                    ),
                }
            )
            self.transition(identity, ["planning"], "awaiting_approval", data)
        except Exception as exc:
            data["failure_category"] = (
                str(exc) if isinstance(exc, PolicyError) else "private_planning_failed"
            )
            data["events"].append(
                {"at": now(), "name": "failed", "detail": data["failure_category"]}
            )
            self.transition(identity, ["planning"], "failed", data)

    def approve(self, identity: str, approved: str) -> dict[str, Any]:
        data = self.get(identity)
        if data.get("approval_digest") != approved or approved != digest(
            {"snapshot": data.get("snapshot"), "plan": data.get("plan")}
        ):
            raise PolicyError("approval_digest_mismatch")
        data["events"].append(
            {"at": now(), "name": "approved", "detail": "Plan accepted; no code has executed"}
        )
        if not self.transition(identity, ["awaiting_approval"], "approved", data):
            raise PolicyError("approval_state_conflict")
        return self.get(identity)

    def stop(self, identity: str, state: str) -> dict[str, Any]:
        # A plan may finish between read and cancellation. Compare its observed state
        # before writing the payload so cancellation cannot erase newer evidence.
        for _ in range(4):
            data = self.get(identity)
            if data["status"] not in {"queued", "planning", "awaiting_approval", "approved"}:
                return data
            data["events"].append({"at": now(), "name": state})
            if self.transition(identity, [data["status"]], state, data):
                return self.get(identity)
        raise PolicyError("cancellation_state_conflict")

    def recover(self) -> None:
        # One application process is supported; never reissue an uncertain model/GitHub write.
        with self.engine.begin() as conn:
            conn.execute(
                update(private_runs)
                .where(private_runs.c.status.in_(["queued", "planning"]))
                .values(status="interrupted")
            )
