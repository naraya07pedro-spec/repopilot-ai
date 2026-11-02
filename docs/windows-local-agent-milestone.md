# Windows local-agent engineering — 1 November 2026

Development continues from 80f91b8 on feat/windows-local-agent. Main and the unmerged PR #8
remain preserved. WSL recovery is deferred by the owner: no WSL diagnostic, service/distro
operation, OpenClaw interruption, installation or virtual-disk change is part of this work.

## Components verified independently of WSL

The release already contains PR #8's shared provider, approval, worker-ledger/transport,
text-only candidate staging and reconciled-publication components. Comparing the owner,
worker_dispatch, worker_contract and private_publish files at 3545a025 and 37c01e9 found them
identical. Those components were reused directly; no sandbox.py or worker_server.py was imported,
and no merge/cherry-pick of the experimental runtime was needed.

The missing owner scheduling integration is now implemented. The authenticated execute route
passes through the unavailable worker gate first; with a future reviewed worker composition it
can persist a job, acquire shared capacity, schedule once and return 202. Concurrent duplicate
requests do not schedule twice. Queue cancellation uses the same atomic state boundary as claim;
active cancellation needs an authenticated receipt. Submission/restart uncertainty never causes
automatic execution replay. Production supplies no worker and still returns 409.

The provider profile now includes request_timeout_seconds (1–120, default 30), bound to approval.
The compatible adapter rejects tool/function requests even if accompanying JSON looks valid.
Publication rechecks the current model binding and accepted receipt digest, and reconciliation
requires an independently read open draft PR. Transport uncertainty still prevents repeated writes.

The HTTP workflow test joins local-profile planning, digest approval, exact text staging,
authenticated receipt handling and separately approved draft publication. Its model, worker and
GitHub responses are **synthetic**. No candidate code is imported, compiled or executed by this
test. It establishes component integration, not a genuine agent acceptance run.

Local Windows verification: **273 passed, five environment skips, 95.44% statement coverage**
(1,864/1,953 statements). Skips are four unconfigured PostgreSQL cases and one Windows symlink
privilege case. Ruff check, format check (80 files) and mypy (26 application modules) passed.
No UI source changed, so a local production frontend build was not repeated. The development
branch's normal GitHub CI must be reported separately from these local results.
Remote [Verify run 41230279122](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/41230279122)
passed backend, frontend and container jobs for exact commit
2da0e9bd8730f1f70ac751416928ace75074e022. No live sandbox job is present on this release branch.

## Actual local runtime and model evidence

This is the 8 GiB Ryzen 5 4500 / Radeon RX 580 PC, not the previous 4 GB laptop. Existing D:
manifests reference Llama 3.2 3B Q4_K_M (2,019,377,376 bytes) and DeepSeek Coder 6.7B
(3,827,819,904 bytes). The Llama GGUF SHA-256 matches its manifest digest; DeepSeek was inventoried
by size, not cryptographically reverified in this milestone. No additional weights were downloaded.

No Ollama/llama.cpp/LM Studio runtime was on PATH or in the inspected common installation
locations. A portable [official llama.cpp b11960 Vulkan archive](https://github.com/ggml-org/llama.cpp/releases/tag/b11960)
was downloaded to D: only: 37,345,851 bytes, about 35.6 MiB. Its SHA-256 matches GitHub's release
asset digest. No installer, global PATH change, dependency/driver package or Windows feature
change was used. The binary reports build 11960 / commit 8642541b2 and enumerates Vulkan0 as
Radeon RX 580, 4,096 MiB total / 3,433 MiB available at that snapshot. This verifies binary
startup and device enumeration, not model inference or a driver performance guarantee.

One bounded Llama loading trial used loopback port 18434, offline mode, one request slot,
two CPU threads, below-normal CPU priority, two logical-CPU affinity, 8,192 context tokens,
quantized KV cache and explicit Vulkan offload. It used fixed public fixture data, supplied no
credentials in model requests and made no external provider call. A 1 GiB initial-headroom check and a 512 MiB
available-RAM floor protect the ongoing workload; only the test-owned server can be stopped.

The RAM guard stopped the owned server after 4.328 seconds before readiness. The minimum
sampled available RAM was 477,200,384 bytes; sampled peak server working set 156,991,488 bytes,
private memory 135,991,296 bytes, and observed CPU time 0.672 seconds. These are initialization
samples, not tokens/second, inference latency or a complete memory-demand estimate. GPU inference
utilization was not captured because readiness was never reached. The exit is an explicit guard
abort, not proof of model corruption or a Vulkan compatibility failure. No generated plan exists
from this trial and no generated code ran. The owned server was confirmed exited.

The owner subsequently approved one smaller test model. Qwen2.5-Coder-0.5B-Instruct Q4_0 was
downloaded to D:, 428,730,240 bytes (about 409 MiB), from the official Qwen repository pinned at
ebb2015119c907b064c512bf053e945850b5875f. Its SHA-256 matches the published LFS object digest.
The [separate provenance record](../evidence/qwen-local-provenance-2026-11-01.json) preserves the
approval, exact source, bytes and digest. No other new model was fetched.

The owner subsequently reported freeing memory. The smaller Vulkan loading trial still reached
the 512 MiB RAM floor before readiness. Native per-PID counters observed 411,607,040 dedicated
GPU bytes, 200,298,496 shared GPU bytes and 14.16% engine activity in an initialization sample.
Those are not inference performance numbers. Only the owned runtime was stopped.

CPU-only loading and inference then worked under the unchanged guards. The first response was
rejected as incomplete at the smaller output allowance. A later schema-valid response repeated
the original bug and was correctly rejected as private_no_change. A 16K-context loading attempt
also hit the memory floor. These outcomes remain in the evidence; a tiny model is not a broadly
validated coding agent. Memory availability fluctuated even after the owner freed applications.

A final **explicitly guided, one-file fixture** asked for the // -> / operator change. With 8,192
context tokens and a 1,536-token output cap, the real compatible adapter discovered the local
model, normalized measured usage, and produced a schema-valid full app.py edit. PrivateService
saved its exact diff/approval binding and stopped at **awaiting_approval**. Static byte comparison
matches the expected one-line fix and preserves the empty-list exception. No code was executed,
no human approval was granted, no worker job/receipt existed and no PR was published.

Measured successful trial: ready in 4.468 seconds; request 11.000 seconds; 262 prompt / 212 output
tokens; observed process CPU time 22.0 seconds; sampled peak working set 726,618,112 bytes and
private memory 410,042,368 bytes; minimum available RAM 863,236,096 bytes. CPU affinity was two
logical CPUs with below-normal priority. GPU offload was explicitly disabled for this successful
trial; GPU inference throughput was not measured. This was an in-process planning smoke with
fixed public fixture data, not a live GitHub App Issue or the full Next/API/model/worker workload.

[Live inference evidence](../evidence/qwen-local-inference-2026-11-01.json) contains the actual
plan/diff, measured usage and earlier failures separately from synthetic integration tests.
The test-owned server exited after the trial. No external application was closed by the agent.

The [compatible-server profile](../deploy/llamacpp-local.example.json) is a startup template for
alias repopilot-local; it does not start a service or download a model. Its output cap now allows
the complete bounded response. scripts/preview_local_fixture.py provides a repeatable data-only
preview against an already running local runtime. It refuses paid profiles, proxy inheritance
and existing output directories, and never approves, writes candidate Python, executes or publishes.
Its wrapper tests use synthetic replies; the live measurement used the same underlying adapter,
planner and service. A later wrapper live preflight was refused for insufficient starting RAM.

Against an already owned, resource-guarded loopback server, with sufficient headroom:

```powershell
.\.venv\Scripts\python.exe scripts/preview_local_fixture.py deploy/llamacpp-local.example.json pc-local-compatible D:\Projects\repopilot-local\new-local-review
```

The output directory must be new. Inspect review.json as untrusted model output; this is a
guided public fixture preview, not real GitHub intake or approval to run its edit.
Final wrapper milestone checks: **277 passed, five environment skips, 95.44% coverage**;
Ruff/format (83 files) and mypy (26 application modules) passed. The shipped profile admits
the fixture at 2,120 encoded request bytes without contacting an endpoint. No UI source changed.
The local measurement harness/logs are under D:\Projects\repopilot-local\runtime-evaluation-2026-11-01.
The sanitized [evidence record](../evidence/windows-local-agent-2026-11-01.json) separates live
binary/load observations from synthetic component tests.

## Acceptance remains blocked

Private execution and publication remain disabled. No sandbox runtime was installed, enabled,
bypassed or retested. PR #8's six failed isolation probes remain authoritative failure evidence.
There is no verified local model -> isolated tests -> draft PR run. A successful model-only
generation would still stop at inspection/approval; it would not authorize host execution.

Local structured generation is verified for the guided fixture only; review the recorded output
without execution. Separately, a compatible isolated worker must pass all existing
security/resource/lifecycle probes before any production dispatcher or publication activation.
The repository-scoped GitHub App and separate publication approval are still required for a
real agent-authored draft. Git CLI development pushes do not supply or validate that App.
