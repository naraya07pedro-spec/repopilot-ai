"""Generate a local-model fixture review only. Never approve, execute or publish code."""

import argparse
import json
from decimal import Decimal
from pathlib import Path

import httpx

from repopilot.fixtures import CATALOG
from repopilot.migrations import migrate
from repopilot.model_adapters import ModelProfile
from repopilot.model_registry import load_profiles
from repopilot.policy import PolicyError
from repopilot.private_planner import BudgetedPlanner
from repopilot.private_service import PrivateService
from repopilot.store import Store


class FixtureSource:
    """Fixed public fixture data, explicitly not a live GitHub App snapshot."""

    allowed = ("naraya07pedro-spec/repopilot-ai",)
    source_roots = {allowed[0]: "fixtures/bug"}

    def snapshot(self, repository: str, number: int) -> dict:
        return {
            "issue": {
                "repository": repository,
                "number": number,
                "title": "Replace // with / in mean",
                "body": (
                    "Replace the // operator with the / operator in app.py. "
                    "mean([1, 2]) must return 1.5. Keep the empty-list ValueError and the rest "
                    "of the function unchanged. Return one complete app.py edit."
                ),
            },
            "files": {"app.py": CATALOG["bug"].files["app.py"]},
            "base_sha": "3545a025c29c9d273e36bbc3a296b4cb6a6ed4b8",
            "base_ref": "main",
            "source_root": "fixtures/bug/",
        }


def preview(profile: ModelProfile, output: Path, client: httpx.Client) -> dict:
    profile = ModelProfile.model_validate(profile.model_dump())
    if profile.paid or client.trust_env:
        raise PolicyError("preview_requires_local_profile_and_no_environment_proxy")
    output.mkdir(exist_ok=False)  # Preserve any previous review or unrelated workspace.
    store = Store(f"sqlite:///{output / 'runs.db'}")
    try:
        migrate(store.engine)
        planner = BudgetedPlanner(
            client, store.engine, "", profile.model, 0, 0, Decimal(0), Decimal(0), profile
        )
        service = PrivateService(store.engine, FixtureSource(), None, {profile.id: planner})
        row, _ = service.create(
            FixtureSource.allowed[0], 1, "local-fixture-preview", model_profile=profile.id
        )
        service.prepare(row["id"])
        report = {
            "source_kind": "guided_builtin_fixture_not_live_GitHub_App",
            "generated_code_executed": False,
            "approval_granted": False,
            "private_execution_enabled": False,
            "publication_performed": False,
            "run": service.get(row["id"]),
        }
        # Edits remain JSON text. No .py file, worker job, receipt or PR is produced.
        (output / "review.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
    finally:
        store.engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profiles", type=Path)
    parser.add_argument("profile_id")
    parser.add_argument("output", type=Path, help="New directory; existing directories are refused")
    args = parser.parse_args()
    profile = next((p for p in load_profiles(str(args.profiles)) if p.id == args.profile_id), None)
    if profile is None:
        parser.error("Profile ID is not configured")
    with httpx.Client(trust_env=False) as client:
        result = preview(profile, args.output, client)
    run = result["run"]
    print(
        json.dumps({"status": run["status"], "usage": run.get("usage"), "output": str(args.output)})
    )


if __name__ == "__main__":
    main()
