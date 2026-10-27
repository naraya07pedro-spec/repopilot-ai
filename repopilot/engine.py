import json
import logging
import time
from pathlib import Path
from typing import Any

from repopilot.fixtures import CATALOG
from repopilot.github import APPROVED_REPO, GitHub
from repopilot.models import Issue, Plan
from repopilot.policy import SECRET, PolicyError, digest, redact, validate_edits
from repopilot.providers import FakeProvider, Provider
from repopilot.runner import Runner
from repopilot.store import Store, now
from repopilot.workspace import apply, assert_snapshot, git, initialize, inspect

logger = logging.getLogger("repopilot")


class Engine:
    def __init__(
        self,
        store: Store,
        workspace: Path,
        provider: Provider | None = None,
        runner: Runner | None = None,
    ):
        self.store, self.workspace = store, workspace
        self.provider = provider or FakeProvider()
        self.runner = runner or Runner()
        workspace.mkdir(parents=True, exist_ok=True)

    def event(self, data: dict[str, Any], name: str, detail: str) -> None:
        data["events"].append({"at": now(), "name": name, "detail": redact(detail)})
        self.store.save(data)
        logger.info(json.dumps({"run_id": data["id"], "event": name, "at": now()}))

    def cancelled(self, identity: str) -> bool:
        return bool(self.store.get(identity)["cancel_requested"])

    def prepare(
        self,
        identity: str,
        issue: Issue | None = None,
        remote: dict[str, Any] | None = None,
    ) -> None:
        if not self.store.claim(identity, "queued", "planning"):
            return
        data = self.store.get(identity)
        started = time.monotonic()
        try:
            fixture = CATALOG[data["scenario"]]
            issue = issue or fixture.issue()
            if remote:
                if issue.repository != APPROVED_REPO:
                    raise PolicyError("repository_not_approved")
                if f"repopilot-scenario: {fixture.name}" not in issue.body:
                    raise PolicyError("issue_scenario_mismatch")
                if not all(c in issue.body for c in fixture.criteria):
                    raise PolicyError("acceptance_criteria_mismatch")
                if remote["files"] != fixture.files:
                    raise PolicyError("remote_fixture_not_audited")
            issue = Issue.model_validate_json(redact(issue.model_dump_json()))
            data["issue"] = issue.model_dump()
            data["source"] = "live-github-fixture" if remote else "local-audited-fixture"
            data["provider"] = self.provider.name
            data["branch"] = "repopilot/" + identity[:12]
            data["remote"] = {k: v for k, v in (remote or {}).items() if k != "files"}
            root = self.workspace / identity
            data["baseline_commit"] = initialize(root, fixture.files, data["branch"])
            context = inspect(root)
            data["inspection"] = context
            self.event(data, "inspected", f"Read {len(fixture.files)} bounded Python files")
            baseline = self.runner.run(
                root, fixture.files, "baseline", lambda: self.cancelled(identity)
            )
            data["checks"].append(baseline.model_dump())
            if baseline.cancelled or self.cancelled(identity):
                self.store.save(data, "cancelled")
                return
            if baseline.timed_out or baseline.exit_code not in (0, 1):
                raise PolicyError("baseline_execution_failed")
            self.event(data, "baseline", f"pytest exit code {baseline.exit_code}")
            for attempt in range(2):
                data["attempts"] = attempt + 1
                try:
                    plan = self.provider.plan(issue, context, fixture)
                    # Runtime validation also covers custom provider implementations.
                    plan = Plan.model_validate(plan.model_dump())
                    break
                except (ValueError, TypeError, AttributeError):
                    self.event(data, "provider_retry", f"Plan attempt {attempt + 1} rejected")
            else:
                raise PolicyError("provider_retry_exhausted")
            edits = {e.path: e.content for e in plan.edits}
            if len(edits) != len(plan.edits):
                raise PolicyError("duplicate_edit_path")
            if set(plan.relevant_files) - set(fixture.files):
                raise PolicyError("unexpected_plan_files")
            validate_edits(edits, fixture.edits)
            if plan.acceptance_criteria != list(fixture.criteria):
                raise PolicyError("plan_acceptance_mismatch")
            if SECRET.search(plan.model_dump_json()):
                raise PolicyError("plan_secret_detected")
            data["plan"] = plan.model_dump()
            data["approval_digest"] = digest(
                {"plan": data["plan"], "baseline": data["baseline_commit"], "issue": data["issue"]}
            )
            data["duration_seconds"] = round(time.monotonic() - started, 3)
            self.event(data, "plan_ready", "Exact plan and baseline bound to approval digest")
            self.store.save(data, "cancelled" if self.cancelled(identity) else "awaiting_approval")
        except Exception as exc:
            self.fail(data, exc)

    def approve(self, identity: str, approval_digest: str) -> None:
        data = self.store.get(identity)
        if data.get("approval_digest") != approval_digest:
            raise PolicyError("approval_digest_mismatch")
        if not self.store.claim(identity, "awaiting_approval", "approved"):
            raise PolicyError("approval_state_conflict")

    def execute(self, identity: str) -> None:
        if not self.store.claim(identity, "approved", "running"):
            return
        data = self.store.get(identity)
        started = time.monotonic()
        try:
            fixture = CATALOG[data["scenario"]]
            root = self.workspace / identity
            if git(root, "rev-parse", "HEAD") != data["baseline_commit"]:
                raise PolicyError("baseline_changed")
            assert_snapshot(root, fixture.files)
            plan = Plan.model_validate(data["plan"])
            if (
                digest(
                    {
                        "plan": data["plan"],
                        "baseline": data["baseline_commit"],
                        "issue": data["issue"],
                    }
                )
                != data["approval_digest"]
            ):
                raise PolicyError("approved_plan_changed")
            edits = {e.path: e.content for e in plan.edits}
            validate_edits(edits, fixture.edits)
            if self.cancelled(identity):
                self.store.save(data, "cancelled")
                return
            apply(root, edits)
            expected = {**fixture.files, **edits}
            assert_snapshot(root, expected)
            data["diff"] = git(root, "diff", "--no-ext-diff", "--no-textconv", "--", *edits)
            data["changed_files"] = sorted(edits)
            git(root, "diff", "--check")
            self.event(data, "edited", f"Applied {len(edits)} approved file changes")
            check = self.runner.run(root, expected, "candidate", lambda: self.cancelled(identity))
            data["checks"].append(check.model_dump())
            data["security_findings"] = [
                {"check": "exact-byte execution gate", "status": "passed"},
                {"check": "sensitive paths and unexpected files", "status": "passed"},
                {"check": "configured secret patterns", "status": "passed"},
                {"check": "arbitrary repository execution", "status": "disabled"},
            ]
            if check.cancelled or self.cancelled(identity):
                self.store.save(data, "cancelled")
                return
            if check.timed_out:
                raise PolicyError("verification_timeout")
            if check.exit_code != 0:
                data["diagnosis"] = "Candidate failed regression tests. No PR is prepared."
                raise PolicyError("verification_failed")
            for kind in ("lint", "format"):
                quality = self.runner.run(
                    root, expected, kind, lambda: self.cancelled(identity), kind=kind
                )
                data["checks"].append(quality.model_dump())
                if quality.cancelled or self.cancelled(identity):
                    self.store.save(data, "cancelled")
                    return
                if quality.timed_out or quality.exit_code != 0:
                    raise PolicyError("quality_check_failed")
            git(root, "add", "--", *edits)
            git(root, "commit", "-m", fixture.title)
            data["commit"] = git(root, "rev-parse", "HEAD")
            data["duration_seconds"] += round(time.monotonic() - started, 3)
            data["pr"] = self.artifact(data, edits)
            self.event(data, "verified", "Candidate tests passed; reviewable PR artifact prepared")
            self.store.save(data, "verified")
        except Exception as exc:
            self.fail(data, exc)

    def artifact(self, data: dict[str, Any], edits: dict[str, str]) -> dict[str, Any]:
        remote = data.get("remote", {})
        body = (
            f"## {data['plan']['interpretation']}\n\n"
            f"Prepared from {data['issue'].get('url') or 'a local seeded fixture issue'}.\n\n"
            f"Provider: {data['provider']}. Source: {data['source']}.\n\n"
            "### Verified checks\n\n"
            + "\n".join(f"- {c['name']}: exit {c['exit_code']}" for c in data["checks"])
            + "\n\n### Reproduce\n\n"
            f"`python -m repopilot.cli demo --scenario {data['scenario']}`\n\n"
            "### Limits\n\nAudited fixture only. No live LLM quality or general sandbox claim. "
            "Human review required; never auto-merge.\n"
        )
        artifact = {
            "repository": APPROVED_REPO,
            "status": "verified",
            "title": data["plan"]["interpretation"],
            "body": body,
            "branch": data["branch"],
            "base_ref": remote.get("base_ref"),
            "base_sha": remote.get("base_sha"),
            "base_tree": remote.get("base_tree"),
            "files": {f"fixtures/{data['scenario']}/{p}": c for p, c in edits.items()},
            "local_commit": data["commit"],
        }
        artifact["digest"] = digest(artifact)
        return artifact

    def fail(self, data: dict[str, Any], exc: Exception) -> None:
        # Never persist raw exception messages (may contain paths, HTTP bodies, secrets).
        data["failure_category"] = (
            redact(str(exc))[:120] if isinstance(exc, PolicyError) else type(exc).__name__
        )
        self.event(data, "failed", data["failure_category"])
        self.store.save(data, "cancelled" if self.cancelled(data["id"]) else "failed")

    def live_prepare(self, identity: str, github: GitHub, issue_number: int, ref: str) -> None:
        try:
            issue = github.issue(APPROVED_REPO, issue_number)
            commit = github.request("GET", f"{APPROVED_REPO}/commits/{ref}")
            scenario = self.store.get(identity)["scenario"]
            files = github.snapshot(APPROVED_REPO, commit["sha"], scenario)
            self.prepare(
                identity,
                issue,
                {
                    "files": files,
                    "base_ref": ref,
                    "base_sha": commit["sha"],
                    "base_tree": commit["commit"]["tree"]["sha"],
                },
            )
        except Exception as exc:
            self.fail(self.store.get(identity), exc)
