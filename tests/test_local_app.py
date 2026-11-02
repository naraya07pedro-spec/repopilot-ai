"""Authenticated local HTTP contracts. Injected transport is explicitly synthetic."""

import time

import httpx
import pytest
from fastapi.testclient import TestClient

from repopilot.local_app import create_local_app
from repopilot.model_adapters import ModelProfile
from repopilot.workspace import initialize
from tests.test_local_agent import SOURCE, response

ORIGIN = "http://127.0.0.1:8765"
TOKEN = "local-session-for-contract-tests-only-12345"
HEADERS = {"Authorization": "Bearer " + TOKEN, "Origin": ORIGIN}


@pytest.fixture
def local_http(tmp_path):
    root = tmp_path / "repo"
    initialize(root, {"app.py": SOURCE}, "local-http-test")
    profiles = (
        ModelProfile(
            id="cpu",
            provider="compatible",
            model="contract-test",
            structured_output="json_schema",
            context_tokens=8192,
            output_tokens=1536,
            context_bytes=8000,
            endpoint="http://127.0.0.1:18434/v1",
        ),
    )
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200, json={"data": [{"id": "contract-test"}]} if request.method == "GET" else response()
        )

    with httpx.Client(transport=httpx.MockTransport(handler), trust_env=False) as transport:
        app = create_local_app(root, tmp_path / "state", profiles, token=TOKEN, client=transport)
        with TestClient(app, base_url=ORIGIN) as client:
            yield client, app.state.agent, calls


def test_host_origin_and_session_are_required(local_http):
    client, _, calls = local_http
    assert client.get("/api/local/settings").status_code == 401
    assert (
        client.get(
            "/api/local/settings", headers={**HEADERS, "Host": "attacker.example"}
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/local/settings", headers={**HEADERS, "Origin": "https://attacker.example"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/local/models/cpu/check",
            json={},
            headers={"Authorization": HEADERS["Authorization"]},
        ).status_code
        == 403
    )
    assert client.get("/api/local/settings", headers=HEADERS).json()["execution_enabled"] is False
    assert not calls


def test_public_shell_static_assets_health_and_disabled_routes(local_http):
    client, _, _ = local_http
    assert "What should change?" in client.get("/").text
    assert client.get("/workspace.js").status_code == 200
    assert client.get("/workspace.css").status_code == 200
    assert "frame-ancestors 'none'" in client.get("/").headers["content-security-policy"]
    assert client.get("/health").json()["publication_enabled"] is False
    for path in ["/api/owner/settings", "/api/local/execute", "/api/local/publish"]:
        assert client.get(path, headers=HEADERS).status_code == 404


def test_http_task_review_export_and_reconnect_history(local_http):
    client, _, calls = local_http
    assert client.get("/api/local/files", headers=HEADERS).json() == ["app.py"]
    assert client.post("/api/local/models/cpu/check", json={}, headers=HEADERS).json()["discovered"]
    result = client.post(
        "/api/local/tasks",
        headers=HEADERS,
        json={
            "task": "Fix fractional mean; preserve all other behavior",
            "paths": ["app.py"],
            "profile": "cpu",
            "request_key": "http-proposal-1",
        },
    )
    assert result.status_code == 200
    identity = result.json()["id"]
    for _ in range(100):
        row = client.get("/api/local/tasks/" + identity, headers=HEADERS).json()
        if row["status"] == "awaiting_approval":
            break
        time.sleep(0.02)
    assert row["status"] == "awaiting_approval"
    assert client.get(f"/api/local/tasks/{identity}/patch", headers=HEADERS).status_code == 409
    assert (
        client.post(
            f"/api/local/tasks/{identity}/approve",
            headers=HEADERS,
            json={"digest": row["approval_digest"]},
        ).status_code
        == 200
    )
    exported = client.get(f"/api/local/tasks/{identity}/patch", headers=HEADERS)
    assert exported.status_code == 200 and "diff --git a/app.py b/app.py" in exported.text
    assert "attachment" in exported.headers["content-disposition"]
    history = client.get("/api/local/tasks", headers=HEADERS).json()
    assert history[0]["status"] == "exported"
    assert "snapshot" not in history[0]
    assert len(calls) == 2


def test_invalid_requests_are_bounded_and_not_found_is_actionable(local_http):
    client, _, calls = local_http
    assert client.post("/api/local/tasks", content="x" * 16385, headers=HEADERS).status_code == 413
    assert client.get("/api/local/tasks/unknown", headers=HEADERS).status_code == 404
    assert (
        client.post("/api/local/tasks", json={"task": "short"}, headers=HEADERS).status_code == 422
    )
    assert not calls
