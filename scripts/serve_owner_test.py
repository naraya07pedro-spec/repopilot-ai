"""Loopback-only browser test server. Synthetic owner; no GitHub/model credentials."""

import tempfile
from pathlib import Path

import httpx
import uvicorn

from repopilot.api import create_app
from repopilot.fixtures import CATALOG
from repopilot.model_adapters import ModelProfile
from repopilot.owner import OwnerConfig
from repopilot.owner_auth import password_hash
from repopilot.providers import FakeProvider


class ContractSource:
    allowed = ("naraya07pedro-spec/repopilot-ai",)

    def repositories(self):
        return list(self.allowed)

    def snapshot(self, repository, number):
        fixture = CATALOG["bug"]
        return {
            "issue": fixture.issue().model_dump(),
            "base_sha": "a" * 40,
            "base_ref": "contract-fixture",
            "files": fixture.files,
            "profile": "synthetic browser contract; no live GitHub/model",
        }


def provider_contract(request):
    if request.method == "GET":
        return httpx.Response(200, json={"models": [{"name": "contract-fixture-no-model"}]})
    fixture = CATALOG["bug"]
    plan = FakeProvider().plan(fixture.issue(), {}, fixture)
    return httpx.Response(
        200,
        json={
            "done": True,
            "done_reason": "stop",
            "message": {"content": plan.model_dump_json()},
            "prompt_eval_count": 100,
            "eval_count": 100,
        },
    )


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="repopilot-browser-") as folder:
        app = create_app(
            workspace=Path(folder),
            owner_config=OwnerConfig(
                mode="owner",
                origin="http://127.0.0.1:3011",
                secure=False,
                password=password_hash("browser-test-password-only"),
                profiles=(
                    ModelProfile(
                        id="browser-local",
                        provider="ollama",
                        model="contract-fixture-no-model",
                        structured_output="json_schema",
                        context_tokens=65536,
                        endpoint="http://127.0.0.1:11434",
                    ),
                ),
            ),
        )
        # Test-only injection. Never dispatches an external request or starts a model.
        with httpx.Client(transport=httpx.MockTransport(provider_contract)) as contract_client:
            owner = app.state.owner
            owner.github = ContractSource()
            owner.service.github = owner.github
            owner.registry.client = contract_client
            owner.registry.planners["browser-local"].client = contract_client
            uvicorn.run(app, host="127.0.0.1", port=8011)
