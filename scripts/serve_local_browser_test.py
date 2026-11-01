"""CI-only local workspace with an explicitly synthetic model transport. Not live evidence."""

import json
import tempfile
from pathlib import Path

import httpx
import uvicorn

from repopilot.local_app import create_local_app
from repopilot.model_adapters import ModelProfile
from repopilot.models import Plan
from repopilot.workspace import initialize

root = Path(tempfile.mkdtemp(prefix="repopilot-browser-contract-"))
repository = root / "browser-contract-repository"
before = "def mean(values):\n    return sum(values) // len(values)\n"
initialize(repository, {"app.py": before}, "browser-contract")
plan = Plan(
    interpretation="Contract-only proposal: preserve fractional means",
    acceptance_criteria=["mean([1, 2]) returns 1.5"],
    relevant_files=["app.py"],
    proposed_changes=["Use true division"],
    tests=["Not executed"],
    risks=["Synthetic browser transport, not a real model run"],
    assumptions=[],
    edits=[{"path": "app.py", "content": before.replace("//", "/")}],
)


def handler(request: httpx.Request) -> httpx.Response:
    if request.method == "GET":
        return httpx.Response(200, json={"data": [{"id": "synthetic-browser-transport"}]})
    return httpx.Response(
        200,
        json={
            "choices": [{"finish_reason": "stop", "message": {"content": plan.model_dump_json()}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 100},
        },
    )


client = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)
profile = ModelProfile(
    id="browser",
    provider="compatible",
    model="synthetic-browser-transport",
    structured_output="json_schema",
    context_tokens=8192,
    output_tokens=1536,
    context_bytes=8000,
    endpoint="http://127.0.0.1:18000/v1",
)
app = create_local_app(
    repository,
    root / "state",
    (profile,),
    port=8875,
    token="browser-contract-only-session-0123456789",
    client=client,
)
if __name__ == "__main__":
    print(
        json.dumps({"mode": "synthetic_browser_transport_only", "execution_enabled": False}),
        flush=True,
    )
    uvicorn.run(app, host="127.0.0.1", port=8875, access_log=False)
