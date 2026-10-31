import json
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from repopilot.api import create_app
from repopilot.fixtures import CATALOG
from repopilot.migrations import budgets, migrate, sessions, versions
from repopilot.owner import OwnerConfig
from repopilot.owner_auth import OwnerAuth, password_hash
from repopilot.policy import PolicyError
from repopilot.private_planner import BudgetedPlanner
from repopilot.private_service import PrivateService
from repopilot.providers import FakeProvider

PASSWORD = "a sufficiently long test password"
ORIGIN = "https://owner.example"
REPO = "naraya07pedro-spec/repopilot-ai"


@pytest.fixture
def config():
    return OwnerConfig(mode="owner", origin=ORIGIN, password=password_hash(PASSWORD))


def snapshot():
    from repopilot.models import Issue

    issue = Issue(number=1, title="Fix mean", body="Preserve fractions", repository=REPO)
    return {
        "issue": issue.model_dump(),
        "base_sha": "a" * 40,
        "files": CATALOG["bug"].files,
        "base_ref": "main",
    }


def result():
    from repopilot.models import Issue

    plan = FakeProvider().plan(Issue.model_validate(snapshot()["issue"]), {}, CATALOG["bug"])
    return {
        "choices": [{"finish_reason": "stop", "message": {"content": plan.model_dump_json()}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 100},
    }


def planner(store, handler=None, **limits):
    migrate(store.engine)
    return BudgetedPlanner(
        httpx.Client(
            transport=httpx.MockTransport(handler or (lambda r: httpx.Response(200, json=result())))
        ),
        store.engine,
        "synthetic-key",
        "test-model",
        limits.get("daily", 1000000),
        limits.get("run", 1000000),
        Decimal("1"),
        Decimal("2"),
    )


class Source:
    allowed = (REPO,)

    def snapshot(self, repository, number):
        return snapshot()

    def repositories(self):
        return [REPO]


def service(store):
    migrate(store.engine)
    return PrivateService(store.engine, Source(), planner(store))


def wait(client, identity):
    for _ in range(200):
        run = client.get("/api/owner/runs/" + identity).json()
        if run["status"] not in {"queued", "planning"}:
            return run
        time.sleep(0.01)
    raise AssertionError("planning did not settle")


def test_owner_session_boundaries_and_migration(tmp_path, config):
    app = create_app(workspace=tmp_path, owner_config=config)
    with TestClient(app, base_url=ORIGIN) as client:
        assert client.get("/api/owner/settings").status_code == 401
        assert client.post("/api/owner/login", json={"password": PASSWORD}).status_code == 403
        assert (
            client.post(
                "/api/owner/login",
                json={"password": PASSWORD},
                headers={"Origin": "https://attacker.example"},
            ).status_code
            == 403
        )
        client.headers["Origin"] = ORIGIN
        assert client.post("/api/owner/login", json={"password": "wrong"}).status_code == 401
        login = client.post("/api/owner/login", json={"password": PASSWORD})
        assert login.status_code == 200
        assert all(
            flag in login.headers["set-cookie"].lower()
            for flag in ["httponly", "secure", "samesite=strict"]
        )
        assert client.get("/api/owner/settings").headers["cache-control"] == "no-store"
        assert client.get("/api/owner/settings").json()["execution_enabled"] is False
        assert client.get("/api/owner/repositories").status_code == 503
        assert client.get("/api/owner/runs/missing").status_code == 404
        assert client.post("/api/demo/runs", json={}).status_code == 403
        assert client.get("/api/runs").status_code == 403
        assert (
            client.post(
                "/api/owner/runs",
                json={"repository": REPO, "issue_number": 1, "idempotency_key": "owner-test"},
            ).status_code
            == 409
        )
        migrate(app.state.store.engine)
        with app.state.store.engine.connect() as conn:
            assert len(conn.execute(select(versions)).all()) == 1
            saved = conn.execute(select(sessions)).mappings().one()
            assert saved["digest"] != client.cookies.get("repopilot_owner")
        assert client.post("/api/owner/logout", json={}).status_code == 200
        assert client.get("/api/owner/settings").status_code == 401


def test_private_plan_approval_cancel_and_no_execution(tmp_path, config):
    app = create_app(workspace=tmp_path, owner_config=config)
    with TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN}) as client:
        owner = app.state.owner
        owner.github = Source()
        owner.planner = planner(app.state.store)
        owner.service = PrivateService(app.state.store.engine, owner.github, owner.planner)
        client.post("/api/owner/login", json={"password": PASSWORD}).raise_for_status()
        assert client.get("/api/owner/repositories").json() == [REPO]
        req = {
            "repository": REPO,
            "issue_number": 1,
            "idempotency_key": "private-plan",
            "paid_approved": True,
        }
        start = client.post("/api/owner/runs", json=req)
        assert start.status_code == 202
        identity = start.json()["id"]
        assert client.post("/api/owner/runs", json=req).json()["id"] == identity
        assert client.post("/api/owner/runs", json={**req, "issue_number": 2}).status_code == 409
        run = wait(client, identity)
        assert run["status"] == "awaiting_approval", run
        assert "+    return sum(values) / len(values)" in run["diff"]
        assert "--- a/app.py" in run["diff"]
        assert client.get("/api/demo/runs").json() == []
        assert client.get("/api/demo/runs/" + identity).status_code == 404
        assert (
            client.post(
                "/api/owner/runs/" + identity + "/approve", json={"digest": "a" * 64}
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/api/owner/runs/" + identity + "/approve", json={"digest": run["approval_digest"]}
            ).json()["status"]
            == "approved"
        )
        assert (
            client.post(
                "/api/owner/runs/" + identity + "/approve", json={"digest": run["approval_digest"]}
            ).status_code
            == 409
        )
        assert client.post("/api/owner/runs/" + identity + "/execute", json={}).status_code == 409
        publish = client.post(
            "/api/owner/runs/" + identity + "/publish", json={"digest": run["approval_digest"]}
        )
        assert publish.status_code == 409
        assert "isolated_worker_unavailable" in publish.json()["detail"]
        assert client.get("/api/owner/runs/" + identity).json()["status"] == "approved"
        assert (
            client.post("/api/owner/runs/" + identity + "/cancel", json={}).json()["status"]
            == "cancelled"
        )
        assert len(client.get("/api/owner/runs").json()) == 1
        assert not list(tmp_path.glob("**/app.py"))


def test_auth_expiry_throttle_and_invalid_hash(store):
    migrate(store.engine)
    auth = OwnerAuth(store.engine, password_hash(PASSWORD))
    token = auth.login(PASSWORD)
    assert auth.valid(token) and not auth.valid("short")
    with store.engine.begin() as conn:
        conn.execute(update(sessions).values(expires=0))
    assert not auth.valid(token)
    assert OwnerAuth(store.engine, "malformed").login(PASSWORD) is None
    assert OwnerAuth(store.engine, "").login(PASSWORD) is None
    for _ in range(4):
        assert auth.login("incorrect") is None
    with pytest.raises(ValueError, match="throttled"):
        auth.login(PASSWORD)
    with pytest.raises(ValueError):
        password_hash("short")


@pytest.mark.parametrize(
    "changes",
    [
        {"mode": "invalid"},
        {"origin": "https://owner.example/path"},
        {"secure": False, "origin": "https://owner.example"},
        {"mode": "owner", "password": ""},
    ],
)
def test_invalid_owner_configuration(changes):
    cfg = OwnerConfig(**changes)
    with pytest.raises(ValueError):
        cfg.validate()


def test_public_mode_never_exposes_owner(tmp_path):
    with TestClient(
        create_app(workspace=tmp_path, owner_config=OwnerConfig(mode="public"))
    ) as client:
        assert (
            client.post(
                "/api/owner/login",
                json={"password": PASSWORD},
                headers={"Origin": "http://localhost:3000"},
            ).status_code
            == 404
        )
        assert client.get("/api/owner/settings").status_code == 401
        assert client.post("/api/demo/runs", json={}).status_code == 403


def test_production_configuration(monkeypatch):
    monkeypatch.setenv("REPOPILOT_ENV", "production")
    with pytest.raises(ValueError):
        OwnerConfig().validate()
    OwnerConfig(mode="owner", origin=ORIGIN, password=password_hash(PASSWORD)).validate()


def test_service_recovery_rejection_and_conflicts(store):
    s = service(store)
    item, fresh = s.create(REPO, 1, "recovery-key", paid_approved=True)
    assert fresh
    assert s.create(REPO, 1, "recovery-key", paid_approved=True)[1] is False
    with pytest.raises(PolicyError):
        s.create(REPO, 2, "recovery-key", paid_approved=True)
    s.recover()
    assert s.get(item["id"])["status"] == "interrupted"
    s.prepare(item["id"])
    assert s.get(item["id"])["status"] == "interrupted"
    item, _ = s.create(REPO, 1, "reject-key", paid_approved=True)
    s.prepare(item["id"])
    assert s.stop(item["id"], "rejected")["status"] == "rejected"
    assert len(s.history()) == 2
    with pytest.raises(KeyError):
        s.get("missing")
    with pytest.raises(PolicyError):
        PrivateService(store.engine, None, None).create(REPO, 1, "missing")
    with pytest.raises(PolicyError):
        PrivateService(store.engine, Source(), None).create(REPO, 1, "missing")


@pytest.mark.parametrize(
    "path", ["../evil.py", ".github/x.py", "other.py", "tests/test_x.py/../evil.py"]
)
def test_private_path_policy(store, path):
    s = service(store)
    data = result()
    plan = json.loads(data["choices"][0]["message"]["content"])
    plan["edits"][0]["path"] = path
    data["choices"][0]["message"]["content"] = json.dumps(plan)
    s.planner = planner(store, lambda r: httpx.Response(200, json=data))
    item, _ = s.create(REPO, 1, "unsafe-key", paid_approved=True)
    s.prepare(item["id"])
    assert s.get(item["id"])["status"] == "failed"


def test_provider_success_and_structured_boundary(store):
    seen = []

    def handler(req):
        data = json.loads(req.content)
        seen.append(data)
        assert req.url.host == "api.openai.com"
        assert data["store"] is False
        assert data["max_completion_tokens"] == 4096
        return httpx.Response(200, json=result())

    p = planner(store, handler)
    plan, usage = p.plan(snapshot())
    assert plan.edits[0].path == "app.py"
    assert usage["prompt_tokens"] == 100 and usage["estimated_cost_micro_usd"] == 300
    assert p.reserved_today() > 300 and len(seen) == 1


@pytest.mark.parametrize("code", [401, 302, 500, 429, 503])
def test_provider_error_and_bounded_retries(store, code):
    calls = []
    p = planner(store, lambda r: calls.append(r) or httpx.Response(code))
    with pytest.raises(PolicyError, match="provider_http"):
        p.plan(snapshot())
    assert len(calls) == (2 if code in {429, 503} else 1)
    assert p.reserved_today() > 0


def test_provider_unknown_timeout_keeps_budget(store):
    calls = []

    def handler(req):
        calls.append(req)
        raise httpx.ReadTimeout("sensitive error text")

    p = planner(store, handler)
    with pytest.raises(PolicyError, match="provider_transport_unknown"):
        p.plan(snapshot())
    assert len(calls) == 1 and p.reserved_today() > 0


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"choices": []},
        {"choices": [{"finish_reason": "length"}]},
        {"choices": [{"finish_reason": "stop", "message": {"refusal": "no"}}]},
        {"choices": [{"finish_reason": "stop", "message": {"content": "invalid"}}]},
        {**result(), "usage": {"prompt_tokens": -1, "completion_tokens": 1}},
    ],
)
def test_provider_invalid_results(store, data):
    p = planner(store, lambda r: httpx.Response(200, json=data))
    with pytest.raises(PolicyError):
        p.plan(snapshot())


def test_budget_and_context_fail_closed(store):
    p = planner(store, run=1)
    with pytest.raises(PolicyError, match="run_budget"):
        p.plan(snapshot())
    assert p.reserved_today() == 0
    p = planner(store)
    with pytest.raises(PolicyError, match="context_limit"):
        p.plan({"file": "x" * 50000})
    p = planner(store, lambda r: httpx.Response(200, text="x" * 64001))
    with pytest.raises(PolicyError, match="output_limit"):
        p.plan(snapshot())
    p = planner(store, daily=1)
    with pytest.raises(PolicyError, match="daily_budget"):
        p.plan(snapshot())


def test_budget_atomic_concurrent_reservation(store):
    p = planner(store, daily=100)

    def reserve(_):
        try:
            p.reserve(100)
            return True
        except PolicyError:
            return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(reserve, range(4))) == 1
    with store.engine.connect() as conn:
        assert conn.execute(select(budgets.c.reserved)).scalar_one() == 100


def test_cancel_preserves_plan_completed_during_race(store, monkeypatch):
    s = service(store)
    item, _ = s.create(REPO, 1, "cancel-race", paid_approved=True)
    original = s.transition
    raced = False

    def racing(identity, before, after, payload=None):
        nonlocal raced
        if after == "cancelled" and not raced:
            raced = True
            s.prepare(identity)
        return original(identity, before, after, payload)

    monkeypatch.setattr(s, "transition", racing)
    stopped = s.stop(item["id"], "cancelled")
    assert stopped["status"] == "cancelled"
    assert stopped["plan"] and stopped["usage"]
    assert [event["name"] for event in stopped["events"]][-2:] == ["plan_ready", "cancelled"]


def test_private_diff_is_derived_without_execution(store, monkeypatch):
    from repopilot.models import Edit, Plan

    s = service(store)
    plan = Plan.model_validate_json(result()["choices"][0]["message"]["content"])
    plan.edits = [Edit(path="tests/test_added.py", content="assert 1 == 1")]
    monkeypatch.setattr(s.planner, "plan", lambda *args: (plan, {}))
    row, _ = s.create(REPO, 1, "preview-new-file", paid_approved=True)
    s.prepare(row["id"])
    data = s.get(row["id"])
    assert data["status"] == "awaiting_approval"
    assert "--- /dev/null" in data["diff"]
    assert "+assert 1 == 1\n\\ No newline at end of file\n" in data["diff"]
    assert "worker_receipt" not in data


def test_noop_and_oversize_private_diffs_fail_closed(store, monkeypatch):
    from repopilot.models import Edit, Plan

    s = service(store)
    plan = Plan.model_validate_json(result()["choices"][0]["message"]["content"])
    plan.edits = [Edit(path="app.py", content=snapshot()["files"]["app.py"])]
    monkeypatch.setattr(s.planner, "plan", lambda *args: (plan, {}))
    row, _ = s.create(REPO, 1, "preview-no-change", paid_approved=True)
    s.prepare(row["id"])
    assert s.get(row["id"])["failure_category"] == "private_no_change"
    plan.edits = [Edit(path=f"tests/test_new_{i}.py", content="x\n" * 12000) for i in range(4)]
    row, _ = s.create(REPO, 1, "preview-too-large", paid_approved=True)
    s.prepare(row["id"])
    assert s.get(row["id"])["failure_category"] == "private_diff_limit"


def test_queued_scope_change_and_conflicting_idempotency_fail_closed(store):
    s = service(store)
    s.github.source_roots = {REPO: "fixtures/bug"}
    row, _ = s.create(REPO, 1, "scope-change-key", paid_approved=True)
    s.github.source_roots = {REPO: "fixtures/feature"}
    with pytest.raises(PolicyError, match="idempotency_conflict"):
        s.create(REPO, 1, "scope-change-key", paid_approved=True)
    s.prepare(row["id"])
    assert s.get(row["id"])["failure_category"] == "repository_scope_changed"


@pytest.mark.parametrize("roots", [["wrong"], {"unapproved/repo": "fixtures"}, {REPO: "../escape"}])
def test_owner_rejects_invalid_source_root_configuration(roots):
    with pytest.raises(PolicyError, match="source_root"):
        OwnerConfig(source_roots=roots, repositories=(REPO,)).validate()


def test_local_doctor_never_reports_secret_values(monkeypatch):
    from repopilot.doctor import report

    monkeypatch.setenv("OPENAI_API_KEY", "private-value-never-print")
    monkeypatch.setenv("REPOPILOT_MODE", "owner")
    monkeypatch.delenv("REPOPILOT_OWNER_PASSWORD_HASH", raising=False)
    result = report()
    assert not result["execution_enabled"] and not result["live_integrations_validated"]
    assert not result["owner_configuration_valid"]
    assert result["provider_credentials_present"]["OPENAI_API_KEY"]
    assert "private-value-never-print" not in json.dumps(result)
    monkeypatch.setenv("REPOPILOT_MODE", "local")
    assert report()["model_profiles"] == 0
