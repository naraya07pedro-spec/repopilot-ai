"""Launch the installed local workspace; no Node, VM or model download is required."""

import argparse
import os
from pathlib import Path

import uvicorn

from repopilot.local_app import create_local_app
from repopilot.model_adapters import ModelProfile
from repopilot.model_registry import load_profiles
from repopilot.policy import PolicyError


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        required=True,
        help="Existing Git repository to inspect; never modified",
    )
    parser.add_argument(
        "--data",
        type=Path,
        help="Private SQLite/checkpoint directory (default: repository/.repopilot/local)",
    )
    parser.add_argument("--profiles", type=Path, help="Owner-configured provider profiles JSON")
    parser.add_argument("--provider", choices=["ollama", "compatible"], default="ollama")
    parser.add_argument("--endpoint", help="Literal loopback endpoint; compatible URLs end in /v1")
    parser.add_argument(
        "--model", help="Already installed runtime model name; no download is attempted"
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--run-budget-micro", type=int, default=0)
    parser.add_argument("--daily-budget-micro", type=int, default=0)
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port from 1024 to 65535")
    if args.run_budget_micro < 0 or args.daily_budget_micro < 0:
        parser.error("Provider budgets cannot be negative")
    try:
        if args.profiles:
            profiles = load_profiles(str(args.profiles))
        elif args.model:
            profiles = (
                ModelProfile(
                    id="local",
                    provider=args.provider,
                    model=args.model,
                    structured_output="json_schema",
                    context_tokens=8192,
                    output_tokens=1536,
                    context_bytes=2560,
                    request_timeout_seconds=120,
                    endpoint=args.endpoint
                    or (
                        "http://127.0.0.1:11434"
                        if args.provider == "ollama"
                        else "http://127.0.0.1:8080/v1"
                    ),
                ),
            )
        else:
            parser.error("Provide --model NAME for an existing local runtime, or --profiles FILE")
        if not profiles:
            parser.error("Model profiles file is empty; configure at least one model")
    except (OSError, ValueError) as error:
        parser.error("Invalid model configuration: " + str(error))
    try:
        app = create_local_app(
            args.repo,
            args.data or args.repo / ".repopilot/local",
            profiles,
            port=args.port,
            paid_enabled=os.environ.get("REPOPILOT_ENABLE_PAID") == "1",
            run_micro=args.run_budget_micro,
            daily_micro=args.daily_budget_micro,
        )
    except (PolicyError, ValueError, OSError) as error:
        parser.error(str(error))
    print(
        f"\nRepoPilot local workspace: http://127.0.0.1:{args.port}/#session={app.state.session_token}",
        flush=True,
    )
    print(
        "Keep this session link private. Only selected source files are sent to your chosen model.",
        flush=True,
    )
    print(
        "Proposal -> review -> patch export. Generated code is never executed or applied. "
        "Ctrl+C stops this workspace.\n",
        flush=True,
    )
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
