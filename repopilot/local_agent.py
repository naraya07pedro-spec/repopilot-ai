"""Local repository intake for the existing durable planning/review service.

Reads selected source; invokes configured adapters; validates proposals as data.
Never imports, executes, installs, applies or publishes repository/model code.
"""

import ast
import difflib
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from repopilot.migrations import private_runs
from repopilot.model_adapters import ModelAdapter
from repopilot.models import Plan
from repopilot.policy import SECRET, PolicyError, digest, safe_path
from repopilot.private_service import PrivateService
from repopilot.store import now
from repopilot.workspace import clean_environment

ACTIVE = ["queued", "inspecting", "planning", "validating"]


class LocalRepository:
    def __init__(self, root: Path):
        absolute = root.absolute()
        if any(p.is_symlink() or p.is_junction() for p in (absolute, *absolute.parents)):
            raise PolicyError("repository_reparse_point")
        self.root = absolute.resolve(strict=True)
        if not self.root.is_dir():
            raise PolicyError("repository_directory_required")
        self.repository = "local/" + digest(str(self.root))[:16]

    def revision(self) -> str:
        executable = shutil.which("git")
        if not executable:
            raise PolicyError("git_missing_install_Git_then_restart")
        try:
            result = subprocess.run(
                [
                    str(Path(executable).resolve()),
                    "--no-pager",
                    "-c",
                    "core.fsmonitor=false",
                    "-c",
                    "core.hooksPath=" + os.devnull,
                    "rev-parse",
                    "--verify",
                    "HEAD",
                ],
                cwd=self.root,
                env=clean_environment(),
                capture_output=True,
                timeout=15,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise PolicyError("repository_git_inspection_timeout") from None
        value = result.stdout.decode("ascii", errors="replace").strip()
        if result.returncode or not re.fullmatch(r"[a-f0-9]{40,64}", value):
            raise PolicyError("repository_needs_a_Git_commit")
        return value

    def files(self) -> list[str]:
        found = []
        visited = 0
        skip = {".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist"}
        for folder, directories, names in os.walk(self.root, followlinks=False):
            directories[:] = sorted(
                d
                for d in directories
                if d not in skip
                and not d.startswith(".")
                and not (Path(folder) / d).is_symlink()
                and not (Path(folder) / d).is_junction()
            )
            visited += len(names) + len(directories)
            for name in sorted(names):
                relative = (Path(folder) / name).relative_to(self.root).as_posix()
                if re.fullmatch(r"[A-Za-z0-9_/-]+\.py", relative):
                    try:
                        self.path(relative)
                        found.append(relative)
                    except PolicyError:
                        continue
                if len(found) >= 500:
                    return found
            if visited >= 10000:
                break
        return found

    def path(self, name: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_/-]+\.py", name):
            raise PolicyError("select_Python_source_paths_only")
        path = safe_path(self.root, name)
        if any(p.is_junction() for p in (path, *path.parents)):
            raise PolicyError("repository_reparse_point")
        return path

    def snapshot(self, task: str, paths: list[str]) -> dict[str, Any]:
        if not paths or len(paths) > 8 or len(set(paths)) != len(paths):
            raise PolicyError("select_one_to_eight_distinct_files")
        files = {}
        total = 0
        for name in paths:
            path = self.path(name)
            if not path.is_file() or path.stat().st_size > 24000:
                raise PolicyError("source_file_missing_or_over_24000_bytes")
            raw = path.read_bytes()
            if b"\0" in raw or b"\r" in raw.replace(b"\r\n", b""):
                raise PolicyError("source_requires_UTF8_LF_or_CRLF_text")
            try:
                files[name] = raw.decode("utf-8")
            except UnicodeError:
                raise PolicyError("source_requires_UTF8") from None
            total += len(raw)
        if total > 32000 or SECRET.search(task + json.dumps(files)):
            raise PolicyError("context_too_large_or_secret_pattern")
        return {
            "issue": {"title": task[:150], "body": task, "repository": self.repository},
            "files": files,
            "base_sha": self.revision(),
            "source_kind": "owner_selected_local_repository",
        }


def proposal(snapshot: dict[str, Any], plan: Plan) -> str:
    """Syntax is parsed only. No imports, evaluation, shell or test execution."""
    if SECRET.search(plan.model_dump_json()):
        raise PolicyError("proposal_secret_pattern")
    paths = [edit.path for edit in plan.edits]
    if len(set(paths)) != len(paths) or set(paths) - set(snapshot["files"]):
        raise PolicyError("proposal_must_edit_distinct_selected_files")
    if set(plan.relevant_files) - set(snapshot["files"]):
        raise PolicyError("proposal_relevant_files_outside_context")
    changes = []
    for edit in plan.edits:
        if "\r" in edit.content or "\0" in edit.content:
            raise PolicyError("proposal_requires_LF_text")
        try:
            ast.parse(edit.content, filename=edit.path)
        except (SyntaxError, ValueError, RecursionError):
            raise PolicyError("proposal_Python_syntax_invalid") from None
        before = snapshot["files"][edit.path]
        after = edit.content.replace("\n", "\r\n") if "\r\n" in before else edit.content
        lines = list(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile="a/" + edit.path,
                tofile="b/" + edit.path,
            )
        )
        if lines:
            changes.append(f"diff --git a/{edit.path} b/{edit.path}\n")
        changes.extend(
            line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
            for line in lines
        )
    patch = "".join(changes)
    if not patch or len(patch.encode()) > 128000:
        raise PolicyError("proposal_empty_or_patch_limit")
    return patch


class LocalAgent(PrivateService):
    """Integrated local source mode, using engineering_runs and existing approval binding."""

    repository: LocalRepository

    def create_task(
        self,
        task: str,
        paths: list[str],
        profile: str,
        request_key: str,
        fallback: str | None = None,
        paid_approved: bool = False,
    ) -> tuple[dict[str, Any], bool]:
        if not 8 <= len(task.strip()) <= 6000 or SECRET.search(task):
            raise PolicyError("task_requires_8_to_6000_characters_without_secrets")
        if len(paths) > 8:
            raise PolicyError("select_at_most_eight_files")
        for name in paths:
            self.repository.path(name)
        for selected in [profile, *([fallback] if fallback else [])]:
            planner = self.selected(selected)
            if planner.profile.paid and not paid_approved:
                raise PolicyError("paid_call_requires_explicit_approval")
        request = {
            "repository": self.repository.repository,
            "issue_number": 0,
            "task": task.strip(),
            "paths": paths,
            "model_profile": profile,
            "requested_profile": profile,
            "fallback": fallback,
            "paid_approved": paid_approved,
        }
        identity = uuid.uuid4().hex
        state = "queued" if paths else "needs_clarification"
        data = {
            "id": identity,
            **request,
            "source_kind": "owner_selected_local_repository",
            "created_at": now(),
            "question": "Select the Python files this task may read and propose edits to."
            if not paths
            else "",
            "attempts": [],
            "events": [{"at": now(), "name": state}],
            "checks_executed": False,
        }
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    private_runs.insert().values(
                        id=identity,
                        request_key=request_key,
                        fingerprint=digest(request),
                        status=state,
                        created_at=data["created_at"],
                        payload=json.dumps(data),
                    )
                )
        except IntegrityError:
            with self.engine.connect() as conn:
                row = (
                    conn.execute(
                        select(private_runs).where(private_runs.c.request_key == request_key)
                    )
                    .mappings()
                    .one()
                )
            if row["fingerprint"] != digest(request):
                raise PolicyError("idempotency_conflict") from None
            return self.get(row["id"]), False
        return self.get(identity), True

    def clarify(self, identity: str, paths: list[str]) -> dict[str, Any]:
        data = self.get(identity)
        if not 1 <= len(paths) <= 8 or len(set(paths)) != len(paths):
            raise PolicyError("select_one_to_eight_distinct_files")
        for path in paths:
            self.repository.path(path)
        data.update(paths=paths, question="")
        if not self.transition(identity, ["needs_clarification"], "queued", data):
            raise PolicyError("clarification_state_conflict")
        return self.get(identity)

    def checkpoint(
        self, identity: str, state: str, after: str, data: dict[str, Any], detail: str
    ) -> bool:
        data["events"].append({"at": now(), "name": after, "detail": detail})
        return self.transition(identity, [state], after, data)

    def prepare(self, identity: str) -> None:
        data = self.get(identity)
        if not self.checkpoint(
            identity, "queued", "inspecting", data, "Read selected files; no repository code runs"
        ):
            return
        state = "inspecting"
        try:
            snapshot = self.repository.snapshot(data["task"], data["paths"])
            data["snapshot"] = snapshot
            data["tools"] = [
                "read_selected_source",
                "invoke_structured_model",
                "parse_Python_syntax",
                "build_unified_patch",
            ]
            correction = ""
            # Maximum TWO model calls total; fallback is opt-in, never silently external.
            for attempt in range(2):
                profile_id = data["requested_profile"]
                if attempt and data["fallback"]:
                    profile_id = data["fallback"]
                planner = self.selected(profile_id)
                request = {**snapshot, **({"correction": correction} if correction else {})}
                _, body = ModelAdapter(planner.profile).request(request)
                encoded = len(json.dumps(body).encode())
                if (
                    encoded > planner.profile.context_bytes
                    or encoded + 4096 + planner.profile.output_tokens
                    > planner.profile.context_tokens
                ):
                    if not data["fallback"] or profile_id == data["fallback"]:
                        raise PolicyError(
                            "selected_model_context_too_small_choose_fewer_files_or_larger_profile"
                        )
                    profile_id = data["fallback"]
                    planner = self.selected(profile_id)
                    _, body = ModelAdapter(planner.profile).request(request)
                    encoded = len(json.dumps(body).encode())
                    if (
                        encoded > planner.profile.context_bytes
                        or encoded + 4096 + planner.profile.output_tokens
                        > planner.profile.context_tokens
                    ):
                        raise PolicyError("fallback_model_context_too_small")
                    data["events"].append(
                        {
                            "at": now(),
                            "name": "capability_routing",
                            "detail": "Explicit fallback has sufficient context: " + profile_id,
                        }
                    )
                data["model_profile"] = profile_id
                data["selection"] = planner.binding()
                if not self.checkpoint(
                    identity,
                    state,
                    "planning",
                    data,
                    f"Model attempt {attempt + 1}/2 using {profile_id}",
                ):
                    return
                state = "planning"
                try:
                    plan, usage = planner.plan(request, retry_http=False)
                    data["attempts"].append(
                        {"profile": profile_id, "usage": usage, "number": attempt + 1}
                    )
                    if not self.checkpoint(
                        identity,
                        state,
                        "validating",
                        data,
                        "Validate selected paths, syntax and patch as data",
                    ):
                        return
                    state = "validating"
                    diff = proposal(snapshot, plan)
                    data.update(
                        plan=plan.model_dump(),
                        diff=diff,
                        usage=usage,
                        approval_expires=int(time.time()) + 3600,
                    )
                    data["approval_digest"] = self.approval_digest(data)
                    self.checkpoint(
                        identity,
                        state,
                        "awaiting_approval",
                        data,
                        "Review exact model proposal; tests have NOT run",
                    )
                    return
                except PolicyError as error:
                    correction = str(error)
                except (ValueError, TypeError, KeyError, IndexError):
                    correction = "provider_invalid_structured_output"
                data["attempts"].append(
                    {"profile": profile_id, "error": correction, "number": attempt + 1}
                )
                if not self.checkpoint(
                    identity, state, state, data, "Bounded correction: " + correction
                ):
                    return
            raise PolicyError("correction_limit_reached: " + correction)
        except Exception as error:
            data["failure_category"] = (
                str(error) if isinstance(error, PolicyError) else "local_planning_failed"
            )
            self.checkpoint(identity, state, "failed", data, data["failure_category"])

    def unchanged(self, data: dict[str, Any]) -> None:
        if self.repository.snapshot(data["task"], data["paths"]) != data.get("snapshot"):
            raise PolicyError("repository_changed_generate_a_new_proposal")
        if self.selected(data["model_profile"]).binding() != data.get("selection"):
            raise PolicyError("model_configuration_changed")

    def approve(self, identity: str, approved: str) -> dict[str, Any]:
        self.unchanged(self.get(identity))
        return super().approve(identity, approved)

    def export_patch(self, identity: str) -> str:
        data = self.get(identity)
        if data["status"] not in {"approved", "exported"}:
            raise PolicyError("approve_exact_proposal_before_export")
        if data.get("approval_expires", 0) < time.time() or data.get(
            "approval_digest"
        ) != self.approval_digest(data):
            raise PolicyError("approval_expired_or_changed")
        self.unchanged(data)
        patch = proposal(data["snapshot"], Plan.model_validate(data["plan"]))
        if patch != data["diff"]:
            raise PolicyError("approved_patch_changed")
        if data["status"] == "approved":
            if not self.checkpoint(
                identity,
                "approved",
                "exported",
                data,
                "Patch downloaded; not applied, tested or published",
            ):
                raise PolicyError("export_state_conflict")
        return patch

    def stop(self, identity: str, state: str) -> dict[str, Any]:
        for _ in range(4):
            data = self.get(identity)
            if data["status"] not in [
                *ACTIVE,
                "needs_clarification",
                "awaiting_approval",
                "approved",
            ]:
                return data
            if self.checkpoint(
                identity,
                data["status"],
                state,
                data,
                "In-flight model result discarded; transport may finish within its timeout",
            ):
                return self.get(identity)
        raise PolicyError("cancellation_state_conflict")

    def recover(self) -> None:
        with self.engine.connect() as conn:
            identities: list[str] = list(
                conn.execute(
                    select(private_runs.c.id).where(private_runs.c.status.in_(ACTIVE))
                ).scalars()
            )
        for identity in identities:
            data = self.get(identity)
            if data["status"] in ACTIVE:
                self.checkpoint(
                    data["id"],
                    data["status"],
                    "interrupted",
                    data,
                    "Restart: no uncertain model call replayed. Retry explicitly.",
                )
