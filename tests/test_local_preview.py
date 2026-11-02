"""Synthetic preview tests; candidate code must stay data and paid calls stay denied."""

import importlib.util
import subprocess
from pathlib import Path

import httpx
import pytest
from test_model_adapters import profile, response

from repopilot.policy import PolicyError

SPEC = importlib.util.spec_from_file_location(
    "local_preview", Path(__file__).resolve().parents[1] / "scripts/preview_local_fixture.py"
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_preview_keeps_real_pipeline_output_as_unapproved_json(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("A preview must never start a process")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    output = tmp_path / "review"
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response("compatible"))),
        trust_env=False,
    ) as client:
        report = module.preview(profile("compatible"), output, client)
        with pytest.raises(FileExistsError):
            module.preview(profile("compatible"), output, client)
    assert report["run"]["status"] == "awaiting_approval"
    assert report["run"]["usage"]["estimated_cost_micro_usd"] == 0
    assert not report["approval_granted"] and not report["generated_code_executed"]
    assert "worker_job" not in report["run"] and "pr" not in report["run"]
    assert {p.name for p in output.iterdir()} == {"runs.db", "review.json"}


@pytest.mark.parametrize("paid,proxy", [(True, False), (False, True)])
def test_paid_or_proxy_inheriting_preview_is_denied_before_any_write(tmp_path, paid, proxy):
    def forbidden(request):
        raise AssertionError("No request may be sent")

    output = tmp_path / "denied"
    with httpx.Client(transport=httpx.MockTransport(forbidden), trust_env=proxy) as client:
        with pytest.raises(PolicyError, match="requires_local"):
            module.preview(profile("openai" if paid else "compatible"), output, client)
    assert not output.exists()


def test_truncated_output_stays_failed_with_no_candidate(tmp_path):
    data = response("compatible")
    data["choices"][0]["finish_reason"] = "length"
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data)), trust_env=False
    ) as client:
        result = module.preview(profile("compatible"), tmp_path / "failed", client)
    assert result["run"]["status"] == "failed"
    assert "approval_digest" not in result["run"] and "plan" not in result["run"]
