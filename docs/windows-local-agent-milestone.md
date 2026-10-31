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
quantized KV cache and explicit Vulkan offload. It used fixed public fixture data and did not
load credentials or an external provider. A 1 GiB initial-headroom check and a 512 MiB
available-RAM floor protect the ongoing workload; only the test-owned server can be stopped.

The RAM guard stopped the owned server after 4.328 seconds before readiness. The minimum
sampled available RAM was 477,200,384 bytes; sampled peak server working set 156,991,488 bytes,
private memory 135,991,296 bytes, and observed CPU time 0.672 seconds. These are initialization
samples, not tokens/second, inference latency or a complete memory-demand estimate. GPU inference
utilization was not captured because readiness was never reached. The exit is an explicit guard
abort, not proof of model corruption or a Vulkan compatibility failure. No generated plan exists
from this trial and no generated code ran. The owned server was confirmed exited.

The smaller-model download choice is pending. Do not fetch new weights automatically while that
choice is pending; the existing 3B trial does not justify weakening the memory guard or closing
OpenClaw/other applications. The owner can instead make headroom available without a WSL change.

The [compatible-server profile](../deploy/llamacpp-local.example.json) is an unvalidated startup
template for alias repopilot-local; it is not a running endpoint or a claim of generation success.
The local measurement harness/logs are under D:\Projects\repopilot-local\runtime-evaluation-2026-11-01.
The sanitized [evidence record](../evidence/windows-local-agent-2026-11-01.json) separates live
binary/load observations from synthetic component tests.

## Acceptance remains blocked

Private execution and publication remain disabled. No sandbox runtime was installed, enabled,
bypassed or retested. PR #8's six failed isolation probes remain authoritative failure evidence.
There is no verified local model -> isolated tests -> draft PR run. A successful model-only
generation would still stop at inspection/approval; it would not authorize host execution.

Next: obtain a genuinely schema-valid local model response within measured PC headroom, then
review it without execution. Separately, a compatible isolated worker must pass all existing
security/resource/lifecycle probes before any production dispatcher or publication activation.
The repository-scoped GitHub App and separate publication approval are still required for a
real agent-authored draft. Git CLI development pushes do not supply or validate that App.
