import base64
import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from repopilot.github_app import GitHubApp
from repopilot.policy import PolicyError

REPO = "naraya07pedro-spec/repopilot-ai"


@pytest.fixture
def key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def adapter(key, handler):
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    return GitHubApp(httpx.Client(transport=httpx.MockTransport(handler)), "123", pem, 456, (REPO,))


def test_jwt_token_scoping_refresh_and_cache(key):
    seen = []

    def handler(req):
        seen.append(req)
        decoded = jwt.decode(
            req.headers["authorization"][7:], key.public_key(), algorithms=["RS256"]
        )
        assert decoded["iss"] == "123" and decoded["exp"] - decoded["iat"] == 600
        if req.method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": 456,
                    "permissions": {
                        "contents": "write",
                        "issues": "read",
                        "pull_requests": "write",
                    },
                },
            )
        import json

        payload = json.loads(req.content)
        assert payload["repositories"] == ["repopilot-ai"]
        return httpx.Response(
            201,
            json={"token": "synthetic-installation-token", "expires_at": "2099-01-01T00:00:00Z"},
        )

    app = adapter(key, handler)
    assert app.token(REPO) == app.token(REPO)
    assert len(seen) == 2
    assert app.repositories() == [REPO]
    app.token(REPO, write=True)
    assert len(seen) == 4
    app.cache[REPO + ":read"] = ("expired", time.time())
    app.token(REPO)
    assert len(seen) == 6
    with pytest.raises(PolicyError, match="not_allowed"):
        app.token("someone/else")


@pytest.mark.parametrize(
    "installation",
    [
        {"id": 123},
        {"id": 456, "suspended_at": "today"},
        {"id": 456, "permissions": {"contents": "read"}},
    ],
)
def test_installation_permissions(key, installation):
    app = adapter(key, lambda r: httpx.Response(200, json=installation))
    with pytest.raises(PolicyError):
        app.token(REPO)


@pytest.mark.parametrize("status", [301, 401, 403, 429, 503])
def test_app_api_failures(key, status):
    seen = []
    app = adapter(key, lambda r: seen.append(r) or httpx.Response(status))
    with pytest.raises(PolicyError):
        app.call("GET", "/app", "synthetic")
    assert len(seen) == (2 if status == 503 else 1)


def test_app_transport_and_response_limit(key):
    seen = []

    def handler(req):
        seen.append(req)
        raise httpx.ReadTimeout("private detail")

    app = adapter(key, handler)
    with pytest.raises(PolicyError, match="transport$"):
        app.call("GET", "/app", "synthetic")
    assert len(seen) == 2
    seen.clear()
    with pytest.raises(PolicyError, match="unknown"):
        app.call("POST", "/app", "synthetic")
    assert len(seen) == 1
    app = adapter(key, lambda r: httpx.Response(200, text="x" * 250001))
    with pytest.raises(PolicyError, match="response_limit"):
        app.call("GET", "/app", "synthetic")


def test_snapshot_immutable_context(key):
    def handler(req):
        path = req.url.path
        if path.endswith("/issues/1"):
            return httpx.Response(200, json={"number": 1, "title": "Issue", "body": "Acceptance"})
        if path.endswith("/commits/main"):
            return httpx.Response(200, json={"sha": "a" * 40})
        if "/git/trees/" in path:
            return httpx.Response(
                200, json={"tree": [{"path": "app.py", "mode": "100644", "type": "blob"}]}
            )
        if "/contents/" in path:
            assert req.url.params["ref"] == "a" * 40
            return httpx.Response(
                200,
                json={"type": "file", "size": 4, "content": base64.b64encode(b"x=1\n").decode()},
            )
        return httpx.Response(200, json={"default_branch": "main"})

    app = adapter(key, handler)
    app.cache[REPO + ":read"] = ("synthetic", time.time() + 3600)
    data = app.snapshot(REPO, 1)
    assert data["files"] == {"app.py": "x=1\n"} and data["base_sha"] == "a" * 40
