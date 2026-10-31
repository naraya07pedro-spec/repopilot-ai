"""Real durable lifecycle and synthetic GitHub responses; no live writes or sandbox."""

import json
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from test_owner import REPO, service, snapshot
from test_worker_contract import KEY, receipt

from repopilot.policy import PolicyError
from repopilot.private_publish import PrivatePublisher
from repopilot.worker_contract import DisabledWorker, WorkerLedger


class Remote:
    allowed = (REPO,)
    source_roots = {REPO: "fixtures/bug"}

    def __init__(self):
        self.client = httpx.Client(transport=httpx.MockTransport(self.request))
        self.writes = []
        self.branch = None
        self.pr = None
        self.lose = None
        self.base = "a" * 40

    def token(self, repo, write=False):
        assert repo == REPO and write
        return "synthetic"

    def snapshot(self, repo, issue):
        return {**snapshot(), "base_tree": "b" * 40, "source_root": "fixtures/bug/"}

    def request(self, req):
        path = req.url.path
        if req.method == "POST":
            body = json.loads(req.content)
            self.writes.append((path, body))
            if path.endswith("/trees"):
                result = {"sha": "c" * 40}
            elif path.endswith("/commits"):
                result = {"sha": "d" * 40}
            elif path.endswith("/refs"):
                self.branch = body["sha"]
                result = {}
            else:
                assert path.endswith("/pulls") and body["draft"] is True
                self.pr = {
                    "number": 42,
                    "body": body["body"],
                    "state": "open",
                    "head": {"sha": "d" * 40, "repo": {"full_name": REPO}},
                    "base": {"ref": "main"},
                }
                result = self.pr
            if path.endswith("/" + str(self.lose)):
                raise httpx.ReadTimeout("remote accepted; acknowledgement lost")
            return httpx.Response(201, json=result)
        if path.endswith("/commits/main"):
            return httpx.Response(200, json={"sha": self.base})
        if "/git/ref/heads/" in path:
            return httpx.Response(200, json={"object": {"sha": self.branch}})
        if "/git/commits/" in path:
            return httpx.Response(
                200, json={"tree": {"sha": "c" * 40}, "parents": [{"sha": "a" * 40}]}
            )
        assert path.endswith("/pulls") and req.url.params["state"] == "all"
        return httpx.Response(200, json=[self.pr] if self.pr else [])


def ready(store):
    s, remote = service(store), Remote()
    s.github = remote
    row, _ = s.create(REPO, 1, "private-publish-test", paid_approved=True)
    identity = row["id"]
    s.prepare(identity)
    s.approve(identity, s.get(identity)["approval_digest"])
    ledger = WorkerLedger(s, KEY)
    order = ledger.claim(ledger.prepare(identity))
    ledger.accept(receipt(order))
    return s, remote, PrivatePublisher(s, lambda: None), identity


def test_publish_binds_receipt_and_scoped_files_and_is_idempotent(store):
    s, remote, publisher, identity = ready(store)
    artifact = publisher.artifact(identity)
    assert set(artifact["files"]) == {"fixtures/bug/app.py"}
    result = publisher.publish(identity, artifact["digest"])
    assert result["status"] == "completed"
    assert result["pr"]["url"] == f"https://github.com/{REPO}/pull/42"
    assert len(remote.writes) == 4
    assert publisher.publish(identity, artifact["digest"]) == result
    assert publisher.reconcile(identity) == result
    assert len(remote.writes) == 4
    assert s.get(identity)["publication"]["commit_sha"] == "d" * 40


def test_production_gate_and_explicit_publication_approval(store):
    s, remote, publisher, identity = ready(store)
    with pytest.raises(PolicyError, match="isolated_worker_unavailable"):
        PrivatePublisher(s, DisabledWorker().require_available).publish(identity, "x")
    with pytest.raises(PolicyError, match="approval_required"):
        publisher.publish(identity, "f" * 64)
    assert remote.writes == []


@pytest.mark.parametrize("operation", ["trees", "commits", "refs", "pulls"])
def test_uncertain_writes_are_never_repeated(store, operation):
    s, remote, publisher, identity = ready(store)
    artifact = publisher.artifact(identity)
    remote.lose = operation
    with pytest.raises(PolicyError, match="outcome_unknown"):
        publisher.publish(identity, artifact["digest"])
    assert s.get(identity)["status"] == "publication_unknown"
    count = len(remote.writes)
    with pytest.raises(PolicyError, match="requires_verified"):
        publisher.publish(identity, artifact["digest"])
    if operation == "pulls":
        assert publisher.reconcile(identity)["status"] == "completed"
    else:
        with pytest.raises(PolicyError):
            publisher.reconcile(identity)
    assert len(remote.writes) == count


def test_stale_base_and_revoked_scope_block_all_writes(store):
    s, remote, publisher, identity = ready(store)
    artifact = publisher.artifact(identity)
    remote.base = "e" * 40
    with pytest.raises(PolicyError, match="base_changed"):
        publisher.publish(identity, artifact["digest"])
    remote.source_roots = {REPO: "fixtures/other"}
    with pytest.raises(PolicyError, match="scope_changed"):
        publisher.publish(identity, artifact["digest"])
    remote.allowed = ()
    with pytest.raises(PolicyError, match="not_authorized"):
        publisher.publish(identity, artifact["digest"])
    assert not remote.writes


@pytest.mark.parametrize("conflict", ["branch", "pr", "duplicate"])
def test_reconciliation_rejects_external_conflicts(store, conflict):
    s, remote, publisher, identity = ready(store)
    remote.lose = "pulls"
    with pytest.raises(PolicyError):
        publisher.publish(identity, publisher.artifact(identity)["digest"])
    if conflict == "branch":
        remote.branch = "f" * 40
    elif conflict == "pr":
        remote.pr["body"] = "unrelated PR"
    else:
        original = remote.request
        remote.client = httpx.Client(
            transport=httpx.MockTransport(
                lambda r: (
                    httpx.Response(200, json=[remote.pr, remote.pr])
                    if r.method == "GET" and r.url.path.endswith("/pulls")
                    else original(r)
                )
            )
        )
    with pytest.raises(PolicyError):
        publisher.reconcile(identity)
    assert s.get(identity)["status"] == "publication_unknown"


def test_concurrent_publication_claim_and_restart(store):
    s, remote, publisher, identity = ready(store)
    approved = publisher.artifact(identity)["digest"]

    def publish(_):
        try:
            return publisher.publish(identity, approved)["status"]
        except PolicyError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(publish, range(2)))
    assert "completed" in outcomes and len(remote.writes) == 4
    s.transition(identity, ["completed"], "preparing_pr")
    s.recover()
    assert s.get(identity)["status"] == "publication_unknown"
    assert publisher.reconcile(identity)["status"] == "completed"
    assert len(remote.writes) == 4


def test_owner_publication_routes_require_auth_origin_and_closed_execution_gate(store, tmp_path):
    from fastapi.testclient import TestClient

    from repopilot.api import create_app
    from repopilot.owner import OwnerConfig
    from repopilot.owner_auth import password_hash

    s, remote, publisher, identity = ready(store)
    origin = "https://owner.example"
    password = "synthetic owner authentication only"
    app = create_app(
        workspace=tmp_path / "api",
        owner_config=OwnerConfig(mode="owner", origin=origin, password=password_hash(password)),
    )
    app.state.owner.service = s
    app.state.owner.publisher = PrivatePublisher(s, DisabledWorker().require_available)
    with TestClient(app, base_url=origin) as client:
        route = f"/api/owner/runs/{identity}"
        assert client.get(route + "/publication").status_code == 401
        client.headers["Origin"] = origin
        client.post("/api/owner/login", json={"password": password}).raise_for_status()
        artifact = client.get(route + "/publication").json()
        assert artifact["digest"] == publisher.artifact(identity)["digest"]
        assert (
            client.post(route + "/publish", json={"digest": artifact["digest"]}).status_code == 409
        )
        assert client.post(route + "/reconcile", json={}).status_code == 409
        assert (
            client.post(
                route + "/publish",
                json={"digest": artifact["digest"]},
                headers={"Origin": "https://evil.example"},
            ).status_code
            == 403
        )
        assert not remote.writes
        remote.lose = "pulls"
        with pytest.raises(PolicyError):
            publisher.publish(identity, artifact["digest"])
        assert client.post(route + "/reconcile", json={}).json()["pr"]["number"] == 42
        assert client.get(route + "/publication").status_code == 409


@pytest.mark.parametrize("change", ["receipt", "candidate", "approval", "base_tree", "scope"])
def test_artifact_cannot_authorize_tampered_evidence(store, change):
    s, _, publisher, identity = ready(store)
    data = s.get(identity)
    if change == "receipt":
        data["worker_receipt"]["checks"][0]["exit_code"] = 1
    elif change == "candidate":
        data["worker_job"]["files"]["app.py"] = "tampered"
    elif change == "approval":
        data["approval_digest"] = "0" * 64
    elif change == "base_tree":
        data["snapshot"]["base_tree"] = None
        data["approval_digest"] = s.approval_digest(data)
    else:
        data["snapshot"]["source_root"] = "../escape/"
        data["approval_digest"] = s.approval_digest(data)
    s.transition(identity, ["verification_passed"], "verification_passed", data)
    with pytest.raises(PolicyError):
        publisher.artifact(identity)


def test_worker_claim_rechecks_source_scope_after_queueing(store):
    s, remote = service(store), Remote()
    s.github = remote
    row, _ = s.create(REPO, 1, "scope-revocation-test", paid_approved=True)
    s.prepare(row["id"])
    s.approve(row["id"], s.get(row["id"])["approval_digest"])
    ledger = WorkerLedger(s, KEY)
    envelope = ledger.prepare(row["id"])
    remote.source_roots = {REPO: "fixtures/other"}
    with pytest.raises(PolicyError, match="source_scope_changed"):
        ledger.claim(envelope)
    assert s.get(row["id"])["status"] == "worker_queued"


def test_publication_rejects_receipt_for_a_different_approval(store):
    from repopilot.policy import digest

    s, _, publisher, identity = ready(store)
    data = s.get(identity)
    data["worker_job"]["approval_digest"] = "0" * 64
    data["worker_receipt"]["job_digest"] = digest(data["worker_job"])
    s.transition(identity, ["verification_passed"], "verification_passed", data)
    with pytest.raises(PolicyError, match="evidence_invalid"):
        publisher.artifact(identity)
