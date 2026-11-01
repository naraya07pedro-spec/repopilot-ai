"""Real Git + deterministic transport contracts. Model/guest execution is NOT claimed."""

import json
import uuid
from decimal import Decimal

import httpx
import pytest

from repopilot.local_agent import LocalAgent, LocalRepository, proposal
from repopilot.local_lock import WorkspaceLease
from repopilot.migrations import migrate
from repopilot.model_adapters import ModelProfile
from repopilot.models import Plan
from repopilot.policy import PolicyError
from repopilot.private_planner import BudgetedPlanner
from repopilot.store import Store
from repopilot.workspace import initialize

SOURCE = "def mean(values):\n    return sum(values) // len(values)\n"
AFTER = SOURCE.replace("//", "/")


def plan(content=AFTER, path="app.py"):
    return Plan(
        interpretation="Preserve fractional means",
        acceptance_criteria=["mean([1, 2]) returns 1.5"],
        relevant_files=["app.py"],
        proposed_changes=["Use true division"],
        tests=["Manually review; tests have not run"],
        risks=["Unexecuted code"],
        assumptions=[],
        edits=[{"path": path, "content": content}],
    )


def response(value=None):
    return {
        "choices": [
            {"finish_reason": "stop", "message": {"content": (value or plan()).model_dump_json()}}
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 100},
    }


@pytest.fixture
def local(tmp_path):
    root = tmp_path / "repo"
    initialize(root, {"app.py": SOURCE}, "local-test")
    store = Store(f"sqlite:///{tmp_path / 'local.db'}")
    migrate(store.engine)
    profile = ModelProfile(
        id="cpu",
        provider="compatible",
        model="contract-test",
        structured_output="json_schema",
        context_tokens=8192,
        output_tokens=1536,
        context_bytes=8000,
        endpoint="http://127.0.0.1:18434/v1",
    )
    calls = []
    answers = [response()]

    def handle(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=answers.pop(0) if len(answers) > 1 else answers[0])

    client = httpx.Client(transport=httpx.MockTransport(handle), trust_env=False)
    planner = BudgetedPlanner(
        client, store.engine, "", profile.model, 0, 0, Decimal(0), Decimal(0), profile
    )
    service = LocalAgent(store.engine, None, None, {profile.id: planner})
    service.repository = LocalRepository(root)
    yield service, root, calls, answers
    client.close()
    store.engine.dispose()


def create(service, **extra):
    return service.create_task(
        "Fix mean([1, 2]) to return 1.5; preserve the function otherwise.",
        ["app.py"],
        "cpu",
        uuid.uuid4().hex,
        **extra,
    )[0]


def test_real_git_read_proposal_approval_and_portable_patch_without_execution(local):
    service, root, calls, _ = local
    row = create(service)
    service.prepare(row["id"])
    row = service.get(row["id"])
    assert row["status"] == "awaiting_approval"
    assert len(calls) == 1
    assert (
        row["usage"]["execution_kind"] == "real_model"
    )  # Adapter metadata; transport above is synthetic.
    assert row["checks_executed"] is False
    with pytest.raises(PolicyError, match="approve_exact"):
        service.export_patch(row["id"])
    service.approve(row["id"], row["approval_digest"])
    patch = service.export_patch(row["id"])
    assert "+    return sum(values) / len(values)" in patch
    assert patch == service.export_patch(row["id"])
    assert service.get(row["id"])["status"] == "exported"
    assert (root / "app.py").read_text() == SOURCE


def test_bounded_correction_with_specific_validation_feedback(local):
    service, _, calls, answers = local
    answers[:] = [response(plan("def invalid(:\n")), response()]
    row = create(service)
    service.prepare(row["id"])
    assert service.get(row["id"])["status"] == "awaiting_approval"
    assert len(calls) == 2
    assert "proposal_Python_syntax_invalid" in calls[1]["messages"][1]["content"]


def test_correction_exhaustion_does_not_approve_or_execute(local):
    service, _, calls, answers = local
    answers[:] = [response(plan(SOURCE))]
    row = create(service)
    service.prepare(row["id"])
    row = service.get(row["id"])
    assert row["status"] == "failed" and len(calls) == 2
    assert "correction_limit_reached" in row["failure_category"]
    assert "approval_digest" not in row


def test_prompt_injection_output_cannot_expand_selected_file_scope(local):
    service, root, calls, answers = local
    answers[:] = [response(plan("raise SystemExit()\n", "../outside.py"))]
    row = create(service)
    service.prepare(row["id"])
    assert service.get(row["id"])["status"] == "failed" and len(calls) == 2
    assert not (root.parent / "outside.py").exists()


def test_model_python_is_never_imported_or_executed(local):
    service, root, _, answers = local
    marker = root / "do-not-create"
    answers[:] = [response(plan(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"))]
    row = create(service)
    service.prepare(row["id"])
    row = service.get(row["id"])
    service.approve(row["id"], row["approval_digest"])
    service.export_patch(row["id"])
    assert not marker.exists()


def test_source_and_approval_tampering_block_export(local):
    service, root, _, _ = local
    row = create(service)
    service.prepare(row["id"])
    row = service.get(row["id"])
    with pytest.raises(PolicyError, match="digest_mismatch"):
        service.approve(row["id"], "0" * 64)
    service.approve(row["id"], row["approval_digest"])
    (root / "app.py").write_text(SOURCE + "# owner changed source\n")
    with pytest.raises(PolicyError, match="repository_changed"):
        service.export_patch(row["id"])


def test_missing_context_clarification_and_duplicate_key(local):
    service, _, calls, _ = local
    row, created = service.create_task("Fix the fractional mean", [], "cpu", "clarify-key")
    assert created and row["status"] == "needs_clarification" and not calls
    row = service.clarify(row["id"], ["app.py"])
    service.prepare(row["id"])
    same, created = service.create_task("Fix the fractional mean", [], "cpu", "clarify-key")
    assert not created and same["id"] == row["id"] and len(calls) == 1
    with pytest.raises(PolicyError, match="idempotency_conflict"):
        service.create_task("Different requirement", [], "cpu", "clarify-key")


def test_cancel_during_model_call_discards_late_result(local, monkeypatch):
    service, _, _, _ = local
    row = create(service)
    planner = service.selected("cpu")
    original = planner.plan

    def cancelling(*args, **kwargs):
        service.stop(row["id"], "cancelled")
        return original(*args, **kwargs)

    monkeypatch.setattr(planner, "plan", cancelling)
    service.prepare(row["id"])
    row = service.get(row["id"])
    assert row["status"] == "cancelled" and "plan" not in row


def test_restart_recovery_never_replays_model_requests(local):
    service, _, calls, _ = local
    row = create(service)
    service.recover()
    assert service.get(row["id"])["status"] == "interrupted" and not calls


def test_explicit_fallback_routing_for_insufficient_context(local):
    service, _, calls, _ = local
    primary = service.selected("cpu")
    small = primary.profile.model_copy(update={"id": "too-small", "context_bytes": 1024})
    service.planners["too-small"] = BudgetedPlanner(
        primary.client, service.engine, "", small.model, 0, 0, Decimal(0), Decimal(0), small
    )
    row, _ = service.create_task(
        "Fix mean([1, 2]) to return 1.5",
        ["app.py"],
        "too-small",
        "explicit-fallback",
        fallback="cpu",
    )
    service.prepare(row["id"])
    row = service.get(row["id"])
    assert row["status"] == "awaiting_approval" and len(calls) == 1
    assert row["model_profile"] == "cpu"
    assert any(e["name"] == "capability_routing" for e in row["events"])


def test_repository_file_listing_and_boundaries(local):
    service, root, _, _ = local
    (root / ".private.py").write_text("private\n")
    (root / "node_modules").mkdir()
    (root / "node_modules/hidden.py").write_text("private\n")
    assert service.repository.files() == ["app.py"]
    for path in ["../app.py", "app.py/../app.py", ".private.py", "CON.py", "file.json"]:
        with pytest.raises(PolicyError):
            service.repository.snapshot("Task", [path])


def test_CRLF_patch_preserves_source_line_endings_without_writing(local):
    service, root, _, _ = local
    (root / "app.py").write_bytes(SOURCE.replace("\n", "\r\n").encode())
    snapshot = service.repository.snapshot("Task", ["app.py"])
    value = proposal(snapshot, plan())
    assert "+    return sum(values) / len(values)\r\n" in value


def test_process_lease_prevents_second_owner_and_releases_without_deleting(tmp_path):
    lease = WorkspaceLease(tmp_path)
    with pytest.raises(PolicyError, match="already_running"):
        WorkspaceLease(tmp_path)
    lease.close()
    second = WorkspaceLease(tmp_path)
    second.close()
    assert (tmp_path / "workspace.lock").exists()
