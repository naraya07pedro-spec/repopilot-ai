import argparse
import json
import os
import uuid
from pathlib import Path

import httpx

from repopilot.engine import Engine
from repopilot.fixtures import CATALOG
from repopilot.github import GitHub
from repopilot.store import Store


def main() -> None:
    parser = argparse.ArgumentParser(description="RepoPilot trusted fixture execution")
    parser.add_argument("command", choices=["demo", "live", "export-fixtures", "publish"])
    parser.add_argument("--scenario", choices=list(CATALOG), default="bug")
    parser.add_argument("--data", type=Path, default=Path(".repopilot"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--issue", type=int)
    parser.add_argument("--ref", default="feat/verified-issue-to-pr")
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--approve-digest")
    args = parser.parse_args()
    if args.command == "export-fixtures":
        for scenario, fixture in CATALOG.items():
            path = Path("fixtures") / scenario
            path.mkdir(parents=True, exist_ok=True)
            for name, content in fixture.files.items():
                (path / name).write_text(content, encoding="utf-8", newline="\n")
        return
    with httpx.Client() as client:
        github = GitHub(client, os.environ.get("GITHUB_TOKEN"))
        if args.command == "publish":
            if not args.artifact or not args.approve_digest:
                parser.error("publish requires --artifact and --approve-digest")
            artifact = json.loads(args.artifact.read_text())
            print(json.dumps(github.publish(artifact, args.approve_digest), indent=2))
            return
        args.data.mkdir(parents=True, exist_ok=True)
        store = Store(f"sqlite:///{args.data.resolve() / 'runs.db'}")
        engine = Engine(store, args.data.resolve() / "workspaces")
        data, _ = store.create(uuid.uuid4().hex, {"scenario": args.scenario}, public=True)
        if args.command == "live":
            if not args.issue:
                parser.error("live requires --issue")
            engine.live_prepare(data["id"], github, args.issue, args.ref)
        else:
            engine.prepare(data["id"])
        data = store.get(data["id"])
        if data["status"] == "awaiting_approval":
            # CLI demo invocation explicitly authorizes only audited fixture edits.
            engine.approve(data["id"], data["approval_digest"])
            engine.execute(data["id"])
        data = store.get(data["id"])
        output = args.output or args.data / f"{data['id']}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, indent=2), encoding="utf-8")
        if data.get("pr"):
            output.with_suffix(".pr.json").write_text(
                json.dumps(data["pr"], indent=2), encoding="utf-8"
            )
        print(json.dumps({"status": data["status"], "id": data["id"], "evidence": str(output)}))
        if data["status"] != "verified":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
