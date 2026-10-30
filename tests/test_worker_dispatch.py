"""Transport tests use synthetic receipts, never a sandbox or candidate execution."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import httpx
import pytest
from test_worker_contract import KEY, job, receipt, setup

from repopilot.policy import PolicyError
from repopilot.worker_contract import Envelope, validate_job
from repopilot.worker_dispatch import WorkerDispatcher, WorkerTransport, candidate_files


def test_real_loopback_transport_and_durable_receipt(store):
    s, _, identity = setup(store)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            assert self.path == "/v1/execute"
            envelope = Envelope.model_validate_json(
                self.rfile.read(int(self.headers["Content-Length"]))
            )
            order = validate_job(envelope, KEY)
            data = receipt(order).model_dump_json().encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with httpx.Client(trust_env=False) as client:
            transport = WorkerTransport(f"http://127.0.0.1:{server.server_port}", KEY, client)
            with pytest.raises(PolicyError, match="isolated_worker_unavailable"):
                WorkerDispatcher(s, KEY, transport).execute(identity)
            assert s.get(identity)["status"] == "approved"
            WorkerDispatcher(s, KEY, transport, lambda: None).execute(identity)
            assert s.get(identity)["status"] == "verification_passed"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://evil.example",
        "http://localhost:8000",
        "http://127.0.0.1:8000/evil",
        "http://user@127.0.0.1:8000",
        "http://127.0.0.1",
    ],
)
def test_transport_endpoint_policy(endpoint):
    with pytest.raises(PolicyError, match="configuration"):
        WorkerTransport(endpoint, KEY, httpx.Client())


@pytest.mark.parametrize("mode", ["timeout", "redirect", "invalid", "oversized", "forged"])
def test_unknown_or_unsafe_transport_never_retries(store, mode):
    s, _, identity = setup(store)
    seen = []

    def handler(request):
        seen.append(request)
        if mode == "timeout":
            raise httpx.ReadTimeout("private detail")
        if mode == "redirect":
            return httpx.Response(302, headers={"location": "https://evil.example"})
        if mode == "invalid":
            return httpx.Response(200, text="not json")
        if mode == "oversized":
            return httpx.Response(200, text="x" * 256001)
        return httpx.Response(200, json={"payload": {}, "signature": "a" * 64})

    transport = WorkerTransport(
        "http://127.0.0.1:8012", KEY, httpx.Client(transport=httpx.MockTransport(handler))
    )
    dispatcher = WorkerDispatcher(s, KEY, transport, lambda: None)
    with pytest.raises(PolicyError, match="uncertain"):
        dispatcher.execute(identity)
    assert len(seen) == 1 and s.get(identity)["status"] == "interrupted"
    with pytest.raises(PolicyError, match="approval_required"):
        dispatcher.execute(identity)
    assert len(seen) == 1


def test_cancel_message_has_distinct_domain_and_acknowledgement(store):
    from repopilot.worker_contract import authenticate

    s, ledger, identity = setup(store)
    order = ledger.claim(ledger.prepare(identity))

    def handler(request):
        envelope = Envelope.model_validate(json.loads(request.content))
        authenticate(envelope, KEY, "cancel")
        with pytest.raises(PolicyError, match="authentication"):
            authenticate(envelope, KEY, "job")
        return httpx.Response(200, json=receipt(order, outcome="cancelled").model_dump())

    transport = WorkerTransport(
        "http://127.0.0.1:8012", KEY, httpx.Client(transport=httpx.MockTransport(handler))
    )
    dispatcher = WorkerDispatcher(s, KEY, transport, lambda: None)
    dispatcher.cancel(identity)
    assert s.get(identity)["status"] == "cancelled"
    dispatcher.cancel(identity)


def test_candidate_files_are_only_text_and_cleanup_is_bounded(tmp_path):
    order = job()
    order.files["tests/test_never_run.py"] = "raise RuntimeError('must not execute')\n"
    with candidate_files(order, tmp_path) as root:
        assert (root / "tests/test_never_run.py").read_text().startswith("raise RuntimeError")
    assert not root.exists() and not list(tmp_path.iterdir())
    with pytest.raises(PolicyError, match="workspace_bytes_changed"):
        with candidate_files(order, tmp_path) as root:
            (root / "app.py").write_text("tampered")
    assert not root.exists()
