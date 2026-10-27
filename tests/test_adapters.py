import base64
import json

import httpx
import pytest

from repopilot.fixtures import CATALOG
from repopilot.github import APPROVED_REPO, GitHub
from repopilot.policy import PolicyError, digest
from repopilot.providers import FakeProvider, OpenAICompatibleProvider


def adapter(handler):
    return GitHub(httpx.Client(transport=httpx.MockTransport(handler)))


def test_github_issue_and_ssrf():
    seen = []

    def handle(req):
        seen.append(req)
        return httpx.Response(200, json={"number": 1, "title": "Bug", "body": "Acceptance"})

    github = adapter(handle)
    issue = github.issue(APPROVED_REPO, 1)
    assert issue.url.endswith("/issues/1")
    assert seen[0].url.host == "api.github.com"
    with pytest.raises(PolicyError):
        github.issue("https://localhost/x", 1)
    with pytest.raises(PolicyError):
        github.issue(APPROVED_REPO, 0)


@pytest.mark.parametrize(
    "status,headers,category",
    [
        (429, {}, "rate_limited"),
        (403, {"x-ratelimit-remaining": "0"}, "rate_limited"),
        (401, {}, "http_401"),
        (302, {"location": "http://127.0.0.1"}, "http_302"),
        (404, {}, "http_404"),
    ],
)
def test_github_errors(status, headers, category):
    github = adapter(lambda req: httpx.Response(status, headers=headers))
    with pytest.raises(PolicyError, match=category):
        github.issue(APPROVED_REPO, 1)


def test_get_retry_but_no_post_retry():
    calls = []

    def handle(req):
        calls.append(req.method)
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    github = adapter(handle)
    assert github.request("GET", APPROVED_REPO) == {"ok": True}
    assert len(calls) == 2
    calls.clear()
    with pytest.raises(PolicyError):
        github.request("POST", APPROVED_REPO + "/pulls", {})
    assert len(calls) == 1


def test_transport_failure():
    calls = []

    def handle(req):
        calls.append(req)
        raise httpx.ReadTimeout("private body")

    github = adapter(handle)
    with pytest.raises(PolicyError, match="github_transport$"):
        github.issue(APPROVED_REPO, 1)
    assert len(calls) == 2
    with pytest.raises(PolicyError, match="unknown"):
        github.request("POST", APPROVED_REPO, {})


def test_reject_pr_and_large_response():
    with pytest.raises(PolicyError, match="not_issue"):
        adapter(lambda r: httpx.Response(200, json={"pull_request": {}})).issue(APPROVED_REPO, 1)
    with pytest.raises(PolicyError, match="response_limit"):
        adapter(lambda r: httpx.Response(200, text="x" * 250001)).issue(APPROVED_REPO, 1)


def test_snapshot_immutable_and_bounded():
    fixture = CATALOG["bug"]
    github = adapter(
        lambda r: httpx.Response(
            200,
            json={
                "type": "file",
                "size": len(fixture.files[r.url.path.split("/")[-1]]),
                "content": base64.b64encode(
                    fixture.files[r.url.path.split("/")[-1]].encode()
                ).decode(),
            },
        )
    )
    assert github.snapshot(APPROVED_REPO, "a" * 40, "bug") == fixture.files
    for ref, scenario in [("main", "bug"), ("a" * 40, "unknown")]:
        with pytest.raises(PolicyError):
            github.snapshot(APPROVED_REPO, ref, scenario)
    github = adapter(lambda r: httpx.Response(200, json={"type": "symlink", "size": 1}))
    with pytest.raises(PolicyError):
        github.snapshot(APPROVED_REPO, "a" * 40, "bug")


def artifact():
    data = {
        "repository": APPROVED_REPO,
        "status": "verified",
        "base_ref": "main",
        "base_sha": "a" * 40,
        "base_tree": "b" * 40,
        "branch": "repopilot/test",
        "title": "Fix",
        "body": "Evidence",
        "files": {"fixtures/bug/app.py": CATALOG["bug"].edits["app.py"]},
    }
    data["digest"] = digest(data)
    return data


def test_publish_order_and_approval():
    calls = []

    def handle(req):
        calls.append((req.method, req.url.path))
        if req.method == "GET":
            return httpx.Response(200, json={"sha": "a" * 40})
        if req.url.path.endswith("/pulls"):
            assert json.loads(req.content)["draft"] is True
            return httpx.Response(201, json={"number": 2})
        return httpx.Response(201, json={"sha": "b" * 40})

    github = adapter(handle)
    data = artifact()
    with pytest.raises(PolicyError):
        github.publish(data, "0" * 64)
    assert not calls
    assert github.publish(data, data["digest"]) == {"number": 2}
    assert [m for m, _ in calls] == ["GET", "POST", "POST", "POST", "POST"]
    assert not any("merge" in path for _, path in calls)


def test_publish_tamper_and_conflict():
    data = artifact()
    github = adapter(lambda r: httpx.Response(200, json={"sha": "c" * 40}))
    with pytest.raises(PolicyError, match="base_changed"):
        github.publish(data, data["digest"])
    data["files"][".github/workflows/evil.yml"] = "malicious"
    with pytest.raises(PolicyError, match="tampered"):
        github.publish(data, data["digest"])


def test_openai_structured_output_and_fixed_origin():
    fixture = CATALOG["bug"]
    plan = FakeProvider().plan(fixture.issue(), {}, fixture)

    def handle(req):
        assert req.url.host == "api.openai.com"
        body = json.loads(req.content)
        assert body["response_format"]["json_schema"]["strict"]
        assert "untrusted_issue" in body["messages"][1]["content"]
        return httpx.Response(
            200, json={"choices": [{"message": {"content": plan.model_dump_json()}}]}
        )

    provider = OpenAICompatibleProvider(
        httpx.Client(transport=httpx.MockTransport(handle)), "configured-model", "unused"
    )
    assert provider.plan(fixture.issue(), {}, fixture) == plan


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"choices": [{"message": {"content": "invalid"}}]}),
        httpx.Response(200, text="x" * 64001),
    ],
)
def test_openai_failures(response):
    provider = OpenAICompatibleProvider(
        httpx.Client(transport=httpx.MockTransport(lambda r: response)), "model", "unused"
    )
    with pytest.raises(PolicyError):
        provider.plan(CATALOG["bug"].issue(), {}, CATALOG["bug"])


def test_live_preparation_uses_remote_issue(engine, store):
    fixture = CATALOG["bug"]
    run, _ = store.create("live", {"scenario": "bug"}, True)

    def handle(req):
        path = req.url.path
        if "/issues/" in path:
            return httpx.Response(
                200,
                json={
                    "number": 7,
                    "title": fixture.title,
                    "body": "repopilot-scenario: bug\n" + "\n".join(fixture.criteria),
                },
            )
        if "/commits/" in path:
            return httpx.Response(
                200, json={"sha": "a" * 40, "commit": {"tree": {"sha": "b" * 40}}}
            )
        name = path.split("/")[-1]
        return httpx.Response(
            200,
            json={
                "type": "file",
                "size": len(fixture.files[name]),
                "content": base64.b64encode(fixture.files[name].encode()).decode(),
            },
        )

    engine.live_prepare(run["id"], adapter(handle), 7, "main")
    data = store.get(run["id"])
    assert data["status"] == "awaiting_approval"
    assert data["source"] == "live-github-fixture"
    engine.approve(run["id"], data["approval_digest"])
    engine.execute(run["id"])
    assert store.get(run["id"])["pr"]["base_sha"] == "a" * 40


def test_live_failure_is_recorded(engine, store):
    run, _ = store.create("live-fail", {"scenario": "bug"}, True)
    engine.live_prepare(run["id"], adapter(lambda r: httpx.Response(404)), 1, "main")
    assert store.get(run["id"])["status"] == "failed"
