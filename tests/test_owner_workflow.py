"""HTTP orchestration with synthetic model/GitHub/worker replies, never a sandbox."""

import json
import threading

import httpx
from fastapi.testclient import TestClient
from test_model_adapters import make_planner, profile, response
from test_owner import ORIGIN, PASSWORD, REPO, wait
from test_owner_dispatch import PendingPool
from test_private_publish import Remote
from test_worker_contract import KEY, receipt

from repopilot.api import create_app
from repopilot.owner import OwnerConfig
from repopilot.owner_auth import password_hash
from repopilot.owner_dispatch import OwnerDispatcher
from repopilot.private_publish import PrivatePublisher
from repopilot.worker_contract import Envelope, validate_job
from repopilot.worker_dispatch import WorkerDispatcher, WorkerTransport, candidate_files


def test_owner_http_plan_approval_staging_receipt_and_draft_contract(tmp_path):
    cfg = OwnerConfig(
        mode="owner", origin=ORIGIN, password=password_hash(PASSWORD), repositories=(REPO,)
    )
    app = create_app(workspace=tmp_path / "owner", owner_config=cfg)
    owner = app.state.owner
    remote = Remote()
    planner = make_planner(
        app.state.store,
        profile("compatible"),
        lambda _: httpx.Response(200, json=response("compatible")),
    )
    owner.service.github = remote
    owner.service.planners["compatible"] = planner
    calls = []

    def handler(request):
        order = validate_job(Envelope.model_validate(json.loads(request.content)), KEY)
        calls.append(order)
        with candidate_files(order, tmp_path) as root:
            assert (root / "app.py").read_bytes() == order.files["app.py"].encode()
        return httpx.Response(200, json=receipt(order).model_dump())

    worker = WorkerDispatcher(
        owner.service,
        KEY,
        WorkerTransport(
            "http://127.0.0.1:8012",
            KEY,
            httpx.Client(transport=httpx.MockTransport(handler), trust_env=False),
        ),
        lambda: None,
    )
    pending = PendingPool()
    with TestClient(app, base_url=ORIGIN) as client:
        assert (
            client.post(
                "/api/owner/login", json={"password": PASSWORD}, headers={"origin": ORIGIN}
            ).status_code
            == 200
        )
        headers = {"origin": ORIGIN}
        row = client.post(
            "/api/owner/runs",
            headers=headers,
            json={
                "repository": REPO,
                "issue_number": 1,
                "model_profile": "compatible",
                "idempotency_key": "owner-workflow-contract",
            },
        ).json()
        identity = row["id"]
        prefix = "/api/owner/runs/" + identity
        plan = wait(client, identity)
        assert plan["status"] == "awaiting_approval"
        assert plan["usage"]["estimated_cost_micro_usd"] == 0
        assert client.post(prefix + "/execute", headers=headers).status_code == 409
        assert not calls
        assert (
            client.post(prefix + "/approve", headers=headers, json={"digest": "f" * 64}).status_code
            == 409
        )
        assert (
            client.post(
                prefix + "/approve", headers=headers, json={"digest": plan["approval_digest"]}
            ).status_code
            == 200
        )
        # Explicit synthetic-only dependency injection, unavailable in production configuration.
        owner.dispatcher = OwnerDispatcher(
            owner.service, pending, threading.BoundedSemaphore(1), worker
        )
        assert client.post(prefix + "/execute").status_code == 403
        queued = client.post(prefix + "/execute", headers=headers)
        assert queued.status_code == 202 and queued.json()["status"] == "worker_queued"
        assert client.post(prefix + "/execute", headers=headers).status_code == 202
        assert len(pending.pending) == 1
        pending.finish()
        assert client.get(prefix).json()["status"] == "verification_passed"
        artifact = client.get(prefix + "/publication").json()
        assert (
            client.post(
                prefix + "/publish", headers=headers, json={"digest": artifact["digest"]}
            ).status_code
            == 409
        )
        assert not remote.writes
        owner.publisher = PrivatePublisher(owner.service, lambda: None)
        published = client.post(
            prefix + "/publish", headers=headers, json={"digest": artifact["digest"]}
        )
        assert published.status_code == 200
        assert published.json()["pr"]["number"] == 42 and remote.pr["draft"] is True
        assert len(remote.writes) == 4 and len(calls) == 1
        assert (
            client.post(
                prefix + "/publish", headers=headers, json={"digest": artifact["digest"]}
            ).status_code
            == 200
        )
        assert len(remote.writes) == 4
    remote.client.close()
