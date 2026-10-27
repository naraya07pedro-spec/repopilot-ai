import time

from fastapi.testclient import TestClient

from repopilot.api import create_app


def wait(client, identity):
    for _ in range(300):
        data = client.get("/api/demo/runs/" + identity).json()
        if data["status"] in {"awaiting_approval", "verified", "failed", "cancelled"}:
            return data
        time.sleep(0.05)
    raise AssertionError("run did not settle")


def test_api_permissions_and_validation(tmp_path):
    with TestClient(create_app(workspace=tmp_path, api_key="operator-test")) as client:
        assert client.get("/health").json()["execution_scope"] == "audited-fixtures-only"
        assert client.get("/api/runs").status_code == 401
        assert client.get("/api/runs", headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert (
            client.get("/api/runs", headers={"Authorization": "Bearer operator-test"}).status_code
            == 200
        )
        assert (
            client.post(
                "/api/demo/runs", json={"scenario": "arbitrary", "idempotency_key": "key12345"}
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/demo/runs",
                json={"scenario": "bug", "idempotency_key": "key12345", "issue_number": 1},
            ).status_code
            == 422
        )
        assert client.get("/api/demo/runs/missing").status_code == 404


def test_api_live_fixture_approval_and_evidence(tmp_path):
    with TestClient(create_app(workspace=tmp_path, api_key="operator-test")) as client:
        req = {"scenario": "bug", "idempotency_key": "api-test-123"}
        result = client.post("/api/demo/runs", json=req)
        assert result.status_code == 202
        identity = result.json()["id"]
        assert client.post("/api/demo/runs", json=req).json()["id"] == identity
        assert client.post("/api/demo/runs", json={**req, "scenario": "feature"}).status_code == 409
        data = wait(client, identity)
        assert data["status"] == "awaiting_approval", data
        assert (
            client.post(f"/api/demo/runs/{identity}/approve", json={"digest": "a" * 64}).status_code
            == 409
        )
        assert (
            client.post(
                f"/api/demo/runs/{identity}/approve", json={"digest": data["approval_digest"]}
            ).status_code
            == 200
        )
        data = wait(client, identity)
        assert data["status"] == "verified", data
        assert len(client.get("/api/demo/runs").json()) == 1
        assert data["checks"][-1]["exit_code"] == 0


def test_private_run_not_visible_in_demo(tmp_path):
    with TestClient(create_app(workspace=tmp_path, api_key="operator-test")) as client:
        headers = {"Authorization": "Bearer operator-test"}
        data = client.post(
            "/api/runs", headers=headers, json={"scenario": "bug", "idempotency_key": "private-run"}
        ).json()
        identity = data["id"]
        assert client.get("/api/demo/runs/" + identity).status_code == 404
        assert client.get("/api/demo/runs").json() == []
        assert (
            client.post(f"/api/demo/runs/{identity}/approve", json={"digest": "a" * 64}).status_code
            == 404
        )
        assert client.get("/api/runs/" + identity, headers=headers).status_code == 200
        assert client.post(f"/api/runs/{identity}/cancel", headers=headers).status_code == 200
