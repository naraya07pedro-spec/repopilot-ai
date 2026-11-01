# Self-hosted proposal edition

RepoPilot runs a stateful task → real model → code proposal → human review → patch export
workflow. It reads selected Python files and never executes, applies or publishes model code.
No GitHub App or API key is required for a local model. The existing isolated-execution and
GitHub publication components remain disabled advanced capabilities.

## Install

Use Windows 11 or Linux with Python 3.12+, Git and a local model runtime you already control.
The Python package bundles the workspace UI; Node, WSL, Hyper-V and Docker are unnecessary.
Choose a new environment directory rather than replacing an existing project's environment.

```powershell
python -m venv .venv-repopilot
.\.venv-repopilot\Scripts\python.exe -m pip install "git+https://github.com/naraya07pedro-spec/repopilot-ai.git@main"
.\.venv-repopilot\Scripts\repopilot.exe local --repo C:\path\to\your\repository --model YOUR_INSTALLED_MODEL
```

Linux:

```sh
python3 -m venv .venv-repopilot
.venv-repopilot/bin/python -m pip install "git+https://github.com/naraya07pedro-spec/repopilot-ai.git@main"
.venv-repopilot/bin/repopilot local --repo /path/to/your/repository --model YOUR_INSTALLED_MODEL
```

The launcher prints a private session link to `http://127.0.0.1:8765/`. Open that link on the
same machine. Its token stays in that browser session and is removed from the address bar.
Never share the link. Nothing binds to a LAN/public interface, enables CORS or creates a tunnel.
If the port is occupied, choose `--port 8766`. Stop with Ctrl+C; other applications are untouched.

For the included starter, clone this repository and use `--repo PATH/TO/repopilot-ai/examples/mean`.
The starter inherits the parent Git revision. Do not run its code through RepoPilot.

## Connect an existing runtime

Ollama's native API is the default, at `http://127.0.0.1:11434`. Start your own Ollama runtime
and choose a model already installed there. RepoPilot does not install Ollama, download weights,
or silently select another model. See [Ollama documentation](https://docs.ollama.com/).

For llama.cpp or another schema-compatible local server:

```sh
repopilot local --repo /path/to/repository --provider compatible --endpoint http://127.0.0.1:8080/v1 --model YOUR_SERVED_MODEL_ALIAS
```

The server must support JSON-schema chat completions and report usage. llama.cpp's
[server documentation](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)
describes local serving and schema-constrained output. The verified CPU-based Qwen model
and runtime are reused; RepoPilot does not rebuild them.

For multiple selectable providers/models, use `--profiles FILE.json`. See
`deploy/llamacpp-local.example.json` and `deploy/local-models.example.json`. Local endpoints
must use literal loopback addresses. Profiles pin the model, schema support, context/output
budgets and request timeout. Defaults allow a small focused file; larger contexts require
an appropriately sized profile and model. Discovery checks the model ID, not coding quality.

OpenAI, Anthropic and Gemini adapters are optional and contract-tested. Their live provider
acceptance has not been performed for this release. To use one, configure its existing
profile/credential environment variable locally, positive rates, `REPOPILOT_ENABLE_PAID=1`,
`--run-budget-micro` and `--daily-budget-micro`. One micro-USD is $0.000001. The UI additionally
requires per-task consent before sending selected source externally. No cloud call occurs
by default; local keys and environment values never reach the frontend.

## Complete a task

1. Check runtime availability. Select a primary profile and optionally an explicit fallback.
2. Choose 1–8 Python files the model may read and edit. Hidden paths, symlinks/junctions,
   traversal, secret patterns, binary files and oversize context are rejected. Only selected
   files are sent. The built-in pattern scan is not exhaustive secret detection.
3. Enter a focused task with acceptance criteria. For `examples/mean/app.py`, request:
   “Replace // with / in app.py. mean([1, 2]) must return 1.5. Preserve the empty-list
   ValueError and all other lines. Return one complete app.py edit.”
4. Follow real saved checkpoints: inspecting → planning → validating → awaiting approval.
   If no files were chosen, the saved task asks for clarification before any model call.
5. Read the diff, assumptions and risks. Validation covers allowed paths, syntax, secret
   patterns, response/patch bounds and actual nonempty changes. **It does not prove behavior.**
6. Approve the exact proposal and download its patch. Approval binds source, model/budget,
   edits and expiry. Export re-reads source and rejects stale/tampered approvals. CRLF source
   is preserved. The patch is not applied. You remain responsible for reviewing and testing
   it in an appropriate environment outside this proposal workflow.

The harness makes at most two model invocations total, including correction/fallback.
It uses the explicit fallback only; no implicit cloud escalation or fixture response exists.
The second attempt receives a validation error or transport failure as bounded correction
context. Context-aware routing can select an explicitly allowed larger-context fallback
before making a call. A 0.5B model may miss requirements or produce unusable output; choose
a stronger model when hardware permits. No quality equivalence with frontier models is claimed.

## Persistence, limits and recovery

SQLite checkpoints live in `REPOSITORY/.repopilot/local` by default. Use `--data D:\path\to\state`
on a Windows PC with limited C: space. This changes only RepoPilot's own storage location.
An OS-released file lease prevents a second launcher from sharing this state while active.
An old lock filename does not require deletion. One model request runs at a time.

Task input is capped at 6,000 characters, context at 32,000 bytes, each source at 24,000 bytes,
edits at four files and patch at 128,000 bytes. The selected model's smaller limits also apply.
Model profiles cap output tokens and network timeout (up to 120 seconds per request).
Cancellation discards late results; the runtime may continue the in-flight request until
its timeout. Cancelling a RepoPilot task never kills a shared runtime or another application.

On restart, uncertain active tasks become interrupted and are never replayed automatically.
Choose Retry as new task explicitly. Completed proposals/history remain available; a new
session token is printed. Approval expires after one hour. Source/configuration changes
require a new proposal and approval.

## Hardware and verification scope

Workspace memory depends on history and Python dependencies; model memory is additional.
The Windows evaluation machine is an 8 GiB PC using CPU-only
Qwen2.5-Coder 0.5B Q4_0 and guarded available memory. Reserve at least 1.5 GiB free before that
combined small-model acceptance; larger models need substantially more. No discrete GPU is
required for the CPU path. An 8 GiB total is a practical tested profile, not a guarantee for
every application mix or model. Linux gets backend/HTTP/packaging CI coverage; a live Linux
local-model acceptance is not claimed. No model runtime/OS feature is installed by setup.

## Common errors

| Message | Action |
| --- | --- |
| Model runtime could not be reached | Start your runtime; verify port, native Ollama vs compatible `/v1`, and model alias |
| Configured model missing | Choose a model already installed in the runtime |
| Model context too small | Select fewer/smaller files or configure a larger-capacity profile/model |
| Correction limit reached | Review the reason, refine the task or select a stronger model, then retry explicitly |
| Repository changed | Generate and approve a fresh proposal |
| Repository needs a Git commit | Select an existing committed repository; RepoPilot does not initialize it automatically |
| Workspace already running | Use the existing launcher or stop that launcher; do not delete the lock file |
| Session required | Open the new private link printed by the current launcher |
| Model busy | Task is saved queued; choose Resume after the current request finishes |

The old trusted-fixture console and authenticated GitHub App owner workspace remain available
as separate existing interfaces. Neither enables unsafe execution for this edition.
