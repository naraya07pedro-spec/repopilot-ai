"""Exercise the production console proxy against a running local engine."""

import json
import time
import uuid
from pathlib import Path

import httpx


def wait(client: httpx.Client, identity: str, expected: set[str]) -> dict:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        response = client.get("/api/demo/runs/" + identity)
        response.raise_for_status()
        run = response.json()
        if run["status"] in expected:
            return run
        if run["status"] in {"failed", "cancelled", "interrupted"}:
            raise AssertionError(run)
        time.sleep(0.5)
    raise TimeoutError("HTTP execution exceeded 90 seconds")


def main() -> None:
    with httpx.Client(base_url="http://127.0.0.1:3000", timeout=15) as client:
        home = client.get("/")
        assert home.status_code == 200 and "RepoPilot" in home.text
        assert home.headers["x-content-type-options"] == "nosniff"
        request = {"scenario": "bug", "idempotency_key": uuid.uuid4().hex}
        response = client.post("/api/demo/runs", json=request)
        assert response.status_code == 202
        identity = response.json()["id"]
        assert client.post("/api/demo/runs", json=request).json()["id"] == identity
        plan = wait(client, identity, {"awaiting_approval"})
        assert plan["checks"][0]["exit_code"] == 1
        assert (
            client.post(
                "/api/demo/runs/" + identity + "/approve", json={"digest": "0" * 64}
            ).status_code
            == 409
        )
        approval = client.post(
            "/api/demo/runs/" + identity + "/approve", json={"digest": plan["approval_digest"]}
        )
        approval.raise_for_status()
        run = wait(client, identity, {"verified"})
        assert run["pr"]["status"] == "verified"
        assert all(check["exit_code"] == 0 for check in run["checks"][1:])
        assert any(item["id"] == identity for item in client.get("/api/demo/runs").json())
        assert (
            client.post(
                "/api/demo/runs", json=request, headers={"Origin": "https://untrusted.invalid"}
            ).status_code
            == 403
        )
        Path("evidence").mkdir(exist_ok=True)
        Path("evidence/http-smoke.json").write_text(
            json.dumps(
                {
                    "result": "passed",
                    "transport": "HTTP through production Next.js proxy",
                    "assertions": [
                        "homepage",
                        "security header",
                        "idempotency",
                        "approval gate",
                        "real baseline and candidate checks",
                        "history",
                        "origin rejection",
                    ],
                    "run": run,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print("Production HTTP smoke passed; evidence/http-smoke.json")


if __name__ == "__main__":
    main()
