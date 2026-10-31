# Local-first correction — 31 October 2026

PR #9 source 18837c52354bc68ba0b9bc7917a8f2edb417f8cd was reverified: open/unmerged,
CI 41165868963 green (247 backend, zero skips, 96.10%; 13 frontend/six browser; builds/audits).
Do not merge automatically. Current follow-up replaces the paid-provider activation path with
local-only setup and records a real read-only Windows audit. It adds bounded zero-cost Ollama
profiles, a repeatable hardware audit and two deterministic zero-budget regression tests.

Actual hardware: one 4 GB module, 3.84 GiB visible, 485–549 MiB available during samples,
i3-8130U 2C/4T, Intel UHD 620, about 33.4 GiB disk free. Firmware virtualization/SLAT true;
hypervisor absent. WSL/VirtualMachinePlatform disabled, wsl --status exits 50, no distro or
Ollama/Podman/Docker. Current session is not elevated. No heavy installs, downloads or settings
changes were made. CPU/GPU/OS model identifiers only are recorded; no hostnames/serials/secrets.

**Zero paid API, zero rented server.** No OpenAI or other model API keys are required. Keep all
paid flags false and budgets zero. The existing Ollama adapter already sets num_ctx/num_predict
and keep_alive=0. Local-only contract checks: 35 passed, including both shipped profiles and
an authenticated zero-budget plan/approval with execution/publication still denied. These use
synthetic HTTP responses, not a real installed model. Full current follow-up CI must be checked.

No practical local model has been validated. Qwen2.5-Coder 0.5B (398 MB Q4) is a smoke candidate;
1.5B (986 MB Q4) is the smallest coding candidate to evaluate, not a measured capability claim.
Weight sizes exclude runtime/context RAM. Current headroom cannot support a credible concurrent
model + app + WSL worker demonstration. No speculative runtime code was added.

Next exact dependency: owner may enable WSL only in Administrator PowerShell using
`wsl --install --no-distribution` and reboot if requested. Then re-audit memory, WSL and kernel
capabilities before any distro/model download. Do not blindly rerun the known failing gVisor
configuration. Verify separation from Windows files/interop and all six preserved live probes
before dispatch activation. Exact GitHub App owner authorization is in owner-activation.md.
Do not ask for model credentials, a VPS or cloud hosting. Do not buy hardware/services.

See [feasibility](local-feasibility.md), [audit record](../evidence/local-hardware-audit-2026-10-31.json)
and [local profiles](../deploy/local-models.example.json). PR #8 remains preserved at 37c01e9.
A genuine Issue → local model → actual isolated tests → draft PR has NOT run. Dispatcher binding,
verified worker lifecycle/recovery and that acceptance remain blocked. Unsafe execution stays off.

## Completed local-first checks

Published follow-up source: d1c0e651b2ab035e88725048bf4d120300787255.
[CI 41169549936](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/41169549936)
passed: 249 backend, zero skips, 96.05% (1,800/1,874), PostgreSQL, Ruff/format/mypy,
13 frontend component and six Chromium cases, private/public builds and audits. Local full
suite: 244 passed, five environment skips, 95.41% (1,788/1,874). No production source change
or new coverage exclusion was needed; the two added tests verify existing local behavior.
The saved PowerShell audit was executed successfully. Standard Ollama install path is absent
and its loopback API is unavailable. No local inference or WSL/sandbox execution is claimed.
Owner WSL administrator action has been requested; no completion was received at this checkpoint.
Next: re-audit only after owner enables WSL. Do not install heavy runtimes/models under the
measured memory load. No paid/provider credential, rented host or automatic merge is required.

## Previous portfolio checkpoint (historical)

# Portfolio release recovery — 31 October 2026

Current branch: `release/v3-portfolio`, based on main `68bf412d6451c7982509d7c5c0ca3ba27826db86`.
The V3 experiment remains preserved in PR #8 / feat/v3-providers at
`37c01e9c6bb77b75940f4072aa8cf0974a8d8b37`, including every sandbox file/test and failure record.
Do not restart or rerun runtime experiments without a compatible environment.

## Release scope

This branch extracts the passing application file set from V3: model adapters/registry, owner
planning/auth/approval/budgets, source scoping, candidate text staging, signed contracts/loopback
transport, publication reconciliation and regression tests. Owner execute and private publication
still use DisabledWorker. No candidate code is imported or executed by private planning.
The main application CI workflow is unchanged; no test or workflow is deleted relative to main.
No sandbox driver/server/image/harness or live sandbox tests are packaged in this application PR.
Their six mandatory failed probes remain in PR #8, which is not being merged wholesale.
See [release boundary](portfolio-release.md) and [source manifest](../evidence/release-scope.json).

## Validated application release checkpoint

Published source: `b611e8272e4318c981006ce4db239f3dd97ee647`.
[PR #9](https://github.com/naraya07pedro-spec/repopilot-ai/pull/9), open/unmerged.
[CI 41165328471](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/41165328471)
passed all three application jobs: 247 backend passed, zero skipped, 96.10% (1,801/1,874),
PostgreSQL, Ruff/format/mypy, 13 component and six Chromium tests, private/public builds,
container smoke and audits. No new coverage exclusions; workflow unchanged from main.

Local: 242 backend passed, five environment skips, 95.36%; 141 targeted contracts and the
approved-plan publication-denial regression passed. TypeScript, 13 frontend tests, private/public
builds and four serial browser cases passed. Two live HTTPS Pages desktop/mobile cases passed;
the real mobile screenshot was inspected. Public private-endpoint requests returned 404.
[Structured evidence](../evidence/v3-portfolio-release-checks-2026-10-31.json). This documentation follow-up
records the measured source checkpoint; verify its current CI in PR #9 before review approval.

PR #8 remains unchanged at 37c01e9 and still fails its mandatory sandbox job. No runtime
experiment was repeated. The app release is eligible for independent human review; the
real coding agent remains incomplete. No automatic merge or deployment occurred.

## Remaining blockers and next action

Review PR #9 and verify the current application CI before any separately approved integration.
No automatic merge or deployment is authorized. Public Pages is already deployed independently.

Real-agent activation remains blocked on a reviewed compatible runtime and dedicated disposable
host, then independent resource/network/filesystem/cancellation/cleanup/recovery validation.
Both released gVisor configurations failed before guest execution. A different ordinary Linux VM
alone does not resolve those defects; see [runtime options/costs](runtime-options.md).
No speculative microVM implementation or paid infrastructure was started.

Owner App/model setup is documented step by step in [owner activation](owner-activation.md).
Credentials and paid-call consent are absent. After isolation passes, the owner dispatcher binding
and the real model → actual isolated tests → draft PR acceptance remain engineering work.
Private cloud and Netlify stay deferred. No unrelated repositories or databases were changed.
