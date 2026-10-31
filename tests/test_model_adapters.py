"""Provider HTTP contract tests. Synthetic responses are not live-model evidence."""

import json
import socket
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient
from test_owner import ORIGIN, PASSWORD, REPO, Source, result, snapshot, wait

from repopilot.api import create_app
from repopilot.migrations import migrate
from repopilot.model_adapters import KEYS, ModelAdapter, ModelProfile
from repopilot.model_registry import ModelRegistry, load_profiles
from repopilot.owner import OwnerConfig
from repopilot.owner_auth import password_hash
from repopilot.policy import PolicyError
from repopilot.private_planner import BudgetedPlanner
from repopilot.private_service import PrivateService

PROVIDERS = ["openai", "anthropic", "gemini", "ollama", "compatible"]


def profile(provider="openai", **changes):
    local = provider in {"ollama", "compatible"}
    return ModelProfile.model_validate(
        {
            "id": provider,
            "provider": provider,
            "model": "test-model",
            "structured_output": "json_schema",
            "context_tokens": 65536,
            "endpoint": (
                "http://127.0.0.1:11434" if provider == "ollama" else "http://127.0.0.1:8080/v1"
            )
            if local
            else "",
            "input_rate": 0 if local else 1,
            "output_rate": 0 if local else 2,
            **changes,
        }
    )


def response(provider):
    content = result()["choices"][0]["message"]["content"]
    if provider == "anthropic":
        return {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": content}],
            "usage": {"input_tokens": 100, "output_tokens": 100},
        }
    if provider == "gemini":
        return {
            "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": content}]}}],
            "usageMetadata": {
                "promptTokenCount": 100,
                "candidatesTokenCount": 90,
                "thoughtsTokenCount": 10,
            },
        }
    if provider == "ollama":
        return {
            "done": True,
            "done_reason": "stop",
            "message": {"content": content},
            "prompt_eval_count": 100,
            "eval_count": 100,
        }
    return result()


def make_planner(store, p, handler):
    migrate(store.engine)
    return BudgetedPlanner(
        httpx.Client(transport=httpx.MockTransport(handler), trust_env=False),
        store.engine,
        "synthetic-key" if p.paid else "",
        p.model,
        1000000 if p.paid else 0,
        1000000 if p.paid else 0,
        Decimal(str(p.input_rate)),
        Decimal(str(p.output_rate)),
        p,
    )


def test_local_timeout_is_explicit_bounded_and_in_approval_binding(store):
    p = profile("compatible", request_timeout_seconds=120)
    seen = []

    def handler(request):
        seen.append(request.extensions["timeout"])
        return httpx.Response(200, json=response("compatible"))

    planner = make_planner(store, p, handler)
    _, usage = planner.plan(snapshot())
    assert seen[0]["read"] == 120
    assert planner.binding()["profile"]["request_timeout_seconds"] == 120
    assert usage["estimated_cost_micro_usd"] == 0
    for invalid in (0, 121):
        with pytest.raises(ValueError):
            profile("compatible", request_timeout_seconds=invalid)


@pytest.mark.parametrize("field", ["tool_calls", "function_call"])
def test_compatible_tool_requests_are_rejected_even_with_valid_plan(store, field):
    data = response("compatible")
    data["choices"][0]["message"][field] = {"name": "must_never_run"}
    planner = make_planner(store, profile("compatible"), lambda _: httpx.Response(200, json=data))
    with pytest.raises(PolicyError, match="unexpected_content"):
        planner.plan(snapshot())


@pytest.mark.parametrize("provider", PROVIDERS)
def test_wire_contract_and_normalized_usage(store, provider):
    p = profile(provider)
    seen = []

    def handler(req):
        seen.append(req)
        data = json.loads(req.content)
        assert "tools" not in data
        if provider == "anthropic":
            assert req.url.path == "/v1/messages"
            assert req.headers["x-api-key"] == "synthetic-key"
            assert data["output_config"]["format"]["type"] == "json_schema"
            assert data["max_tokens"] == 4096
        elif provider == "gemini":
            assert req.url.path == "/v1beta/models/test-model:generateContent"
            assert "key=" not in str(req.url)
            assert req.headers["x-goog-api-key"] == "synthetic-key"
            assert data["generationConfig"]["responseMimeType"] == "application/json"
        elif provider == "ollama":
            assert req.url.path == "/api/chat" and data["stream"] is False
            assert data["options"]["num_predict"] == 4096
            assert data["format"]["additionalProperties"] is False
            assert data["options"]["num_ctx"] == p.context_tokens
            assert data["keep_alive"] == 0  # Release model memory before later worker evaluation.
        else:
            assert req.url.path == "/v1/chat/completions"
            assert data["response_format"]["json_schema"]["strict"] is True
        if not p.paid:
            assert "authorization" not in req.headers and "x-api-key" not in req.headers
        return httpx.Response(200, json=response(provider))

    planner = make_planner(store, p, handler)
    plan, usage = planner.plan(snapshot())
    assert plan.edits[0].path == "app.py"
    assert usage["provider"] == provider and usage["completion_tokens"] == 100
    assert usage["estimated_cost_micro_usd"] == (300 if p.paid else 0)
    assert len(seen) == 1


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://evil.example/v1",
        "http://localhost:8080/v1",
        "http://169.254.169.254:80/v1",
        "http://127.0.0.1:8080/v1?key=secret",
        "http://user:pass@127.0.0.1:8080/v1",
        "http://127.0.0.1:8080/redirect",
        "http://127.0.0.1/v1",
    ],
)
def test_local_endpoint_ssrf_boundaries(endpoint):
    with pytest.raises(ValueError):
        profile("compatible", endpoint=endpoint)


def test_profile_constraints_and_file_validation(tmp_path):
    for changes in [
        {"structured_output": "text"},
        {"input_rate": float("nan")},
        {"endpoint": "https://evil.example"},
        {"context_tokens": 8192},
        {"output_tokens": 9000},
        {"credential": "must-not-be-accepted"},
    ]:
        with pytest.raises(ValueError):
            profile(**changes)
    path = tmp_path / "profiles.json"
    assert load_profiles("") == ()
    path.write_text(json.dumps([profile("ollama").model_dump()]))
    assert load_profiles(str(path))[0].provider == "ollama"
    for data in [{}, [profile().model_dump()] * 2, [profile().model_dump()] * 21]:
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError):
            load_profiles(str(path))
    path.write_text(" " * 32001)
    with pytest.raises(ValueError, match="file_limit"):
        load_profiles(str(path))


@pytest.mark.parametrize("provider", PROVIDERS)
def test_refusals_and_truncation_fail_closed(store, provider):
    data = response(provider)
    if provider == "anthropic":
        data["stop_reason"] = "max_tokens"
    elif provider == "gemini":
        data["candidates"][0]["finishReason"] = "SAFETY"
    elif provider == "ollama":
        data["done_reason"] = "length"
    else:
        data["choices"][0]["finish_reason"] = "length"
    p = make_planner(store, profile(provider), lambda _: httpx.Response(200, json=data))
    with pytest.raises(PolicyError, match="incomplete"):
        p.plan(snapshot())


@pytest.mark.parametrize("provider", PROVIDERS)
def test_discovery_uses_actual_provider_shape(provider):
    p = profile(provider)
    data = (
        {"models": [{"name": "models/test-model"}]}
        if provider == "gemini"
        else (
            {"models": [{"name": "test-model"}]}
            if provider == "ollama"
            else {"data": [{"id": "test-model"}]}
        )
    )
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data)))
    assert ModelAdapter(p, "synthetic-key").discover(client) == ["test-model"]


@pytest.mark.parametrize("provider", ["anthropic", "gemini"])
def test_discovery_pagination_is_bounded(provider):
    seen = []
    data = (
        {"models": [], "nextPageToken": "next"}
        if provider == "gemini"
        else {"data": [], "has_more": True, "last_id": "last"}
    )

    def handler(req):
        seen.append(req)
        return httpx.Response(200, json=data)

    with pytest.raises(PolicyError, match="discovery_limit"):
        ModelAdapter(profile(provider)).discover(
            httpx.Client(transport=httpx.MockTransport(handler))
        )
    assert len(seen) == 10 and seen[1].url.query


def test_registry_default_deny_and_secret_free_status(store, monkeypatch):
    migrate(store.engine)
    for key in KEYS.values():
        if key:
            monkeypatch.delenv(key, raising=False)
    profiles = tuple(profile(p) for p in PROVIDERS)
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503)))
    registry = ModelRegistry(client, store.engine, profiles, 0, 0, False)
    assert [p["available"] for p in registry.catalog()] == [False, False, False, True, True]
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key")
    registry = ModelRegistry(client, store.engine, profiles, 1000000, 1000000, False)
    assert registry.catalog()[0]["reason"] == "paid_calls_disabled_or_budget_missing"
    assert "synthetic-key" not in json.dumps(registry.catalog())
    with pytest.raises(PolicyError, match="not_allowed"):
        registry.discover("not-listed")
    with pytest.raises(PolicyError, match="credentials_missing"):
        registry.discover("anthropic")
    with pytest.raises(PolicyError, match="provider_http_503"):
        registry.discover("ollama")


def test_real_unavailable_loopback_endpoint_is_not_simulated(store):
    # Real connection-refused check; no model is installed or claimed.
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]  # Bound but not listening throughout the check.
        p = profile("ollama", endpoint=f"http://127.0.0.1:{port}")
        with httpx.Client(trust_env=False) as client:
            registry = ModelRegistry(client, store.engine, (p,), 0, 0, False)
            with pytest.raises(PolicyError, match="provider_transport_unknown"):
                registry.discover(p.id)


def test_paid_authorization_selection_budget_and_expiry(store):
    planner = make_planner(store, profile(), lambda _: httpx.Response(200, json=result()))
    s = PrivateService(store.engine, Source(), None, {"openai": planner})
    with pytest.raises(PolicyError, match="explicit_approval"):
        s.create(REPO, 1, "no-paid-consent", model_profile="openai")
    with pytest.raises(PolicyError, match="not_allowed"):
        s.create(
            REPO, 1, "over-budget", model_profile="openai", run_micro=1000001, paid_approved=True
        )
    row, _ = s.create(
        REPO, 1, "selected-model", model_profile="openai", run_micro=200000, paid_approved=True
    )
    with pytest.raises(PolicyError, match="idempotency_conflict"):
        s.create(
            REPO, 1, "selected-model", model_profile="openai", run_micro=300000, paid_approved=True
        )
    s.prepare(row["id"])
    data = s.get(row["id"])
    assert data["status"] == "awaiting_approval"
    assert data["selection"]["profile"]["provider"] == "openai"
    data["selection"]["run_micro"] += 1
    s.transition(row["id"], ["awaiting_approval"], "awaiting_approval", data)
    with pytest.raises(PolicyError, match="digest_mismatch"):
        s.approve(row["id"], data["approval_digest"])
    data["approval_expires"] = 0
    s.transition(row["id"], ["awaiting_approval"], "awaiting_approval", data)
    with pytest.raises(PolicyError, match="expired"):
        s.approve(row["id"], data["approval_digest"])


def test_configuration_change_prevents_transmission(store):
    calls = []
    p = make_planner(store, profile("ollama"), lambda r: calls.append(r))
    s = PrivateService(store.engine, Source(), None, {"ollama": p})
    row, _ = s.create(REPO, 1, "config-change", model_profile="ollama", run_micro=0)
    p.profile = profile("ollama", model="changed-model")
    s.prepare(row["id"])
    assert s.get(row["id"])["failure_category"] == "model_configuration_changed"
    assert not calls


def test_owner_registry_and_discovery_authentication(tmp_path):
    cfg = OwnerConfig(
        mode="owner", origin=ORIGIN, password=password_hash(PASSWORD), profiles=(profile("ollama"),)
    )
    app = create_app(workspace=tmp_path, owner_config=cfg)
    with TestClient(app, base_url=ORIGIN) as client:
        assert client.post("/api/owner/models/ollama/discover").status_code == 403
        client.headers["Origin"] = ORIGIN
        assert client.post("/api/owner/models/ollama/discover").status_code == 401
        client.post("/api/owner/login", json={"password": PASSWORD}).raise_for_status()
        settings = client.get("/api/owner/settings").json()
        assert settings["models"][0]["provider"] == "ollama"
        assert settings["execution_enabled"] is False
        mock = httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"models": [{"name": "test-model"}]})
            )
        )
        app.state.owner.registry.client = mock
        assert client.post("/api/owner/models/ollama/discover").json()["discovered"]
        assert client.post("/api/owner/models/unknown/discover").status_code == 409
        mock.close()


@pytest.mark.parametrize("provider", ["anthropic", "gemini", "ollama"])
def test_provider_unexpected_content_and_usage(store, provider):
    data = response(provider)
    if provider == "anthropic":
        data["content"] = [{"type": "tool_use"}]
    elif provider == "gemini":
        data["candidates"][0]["content"]["parts"] = [{"functionCall": {}}]
    else:
        data["message"]["tool_calls"] = [{}]
    p = make_planner(store, profile(provider), lambda _: httpx.Response(200, json=data))
    with pytest.raises(PolicyError, match="unexpected_content"):
        p.plan(snapshot())


def test_shipped_local_profiles_fit_fixture_and_need_no_paid_budget(store):
    for p in load_profiles("deploy/local-models.example.json"):
        assert not p.paid and p.input_rate == p.output_rate == 0
        planner = make_planner(store, p, lambda _: httpx.Response(200, json=response("ollama")))
        plan, usage = planner.plan(snapshot(), run_micro=0)
        assert plan.edits[0].path == "app.py"
        assert usage["estimated_cost_micro_usd"] == usage["reserved_micro_usd"] == 0


def test_zero_budget_local_owner_plan_approval_keeps_execution_closed(tmp_path, monkeypatch):
    for key in KEYS.values():
        if key:
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("REPOPILOT_ALLOW_PAID_MODELS", "false")
    p = load_profiles("deploy/local-models.example.json")[0]
    cfg = OwnerConfig(mode="owner", origin=ORIGIN, password=password_hash(PASSWORD), profiles=(p,))
    app = create_app(workspace=tmp_path, owner_config=cfg)
    with TestClient(app, base_url=ORIGIN, headers={"Origin": ORIGIN}) as client:
        owner = app.state.owner
        owner.github = Source()
        owner.service.github = owner.github
        planner = owner.registry.planners[p.id]
        with httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response("ollama"))),
            trust_env=False,
        ) as local:
            planner.client = local
            client.post("/api/owner/login", json={"password": PASSWORD}).raise_for_status()
            start = client.post(
                "/api/owner/runs",
                json={
                    "repository": REPO,
                    "issue_number": 1,
                    "idempotency_key": "zero-budget-local",
                    "model_profile": p.id,
                    "run_limit_micro_usd": 0,
                },
            )
            assert start.status_code == 202
            identity = start.json()["id"]
            data = wait(client, identity)
            assert data["status"] == "awaiting_approval", data
            assert data["usage"]["estimated_cost_micro_usd"] == 0
            approve = client.post(
                f"/api/owner/runs/{identity}/approve", json={"digest": data["approval_digest"]}
            )
            assert approve.json()["status"] == "approved"
            assert client.post(f"/api/owner/runs/{identity}/execute", json={}).status_code == 409
            assert (
                client.post(
                    f"/api/owner/runs/{identity}/publish", json={"digest": data["approval_digest"]}
                ).status_code
                == 409
            )
