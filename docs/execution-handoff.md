# Disposable CI isolation experiment — 30 October 2026

All backend/frontend/container checks passed on `d9b57896f60dfb1b430a09afdd77bb8e6de83e12`
([CI 41045767443](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/41045767443)),
including the worker tooling-image build. This follow-up tries the existing disposable Linux CI
VM as a real rootless runsc test host. It contains no model/App credentials and runs only the six
bounded security fixtures. No host security settings are weakened; no private runtime is deployed.

Next exact action: inspect the sandbox job on this PR head. Fix actual driver/test defects; if the
runner lacks required rootless/cgroup/runtime properties, record the specific failure without
weakening controls. The owner execution gate remains closed regardless of CI test availability.

## Prior implementation handoff

# RepoPilot V3 continuation — 30 October 2026

Repository: naraya07pedro-spec/repopilot-ai. Branch: `feat/v3-providers`.
[PR #8](https://github.com/naraya07pedro-spec/repopilot-ai/pull/8) remains open and unmerged.
Latest verified runtime implementation: `34bfb83eeb93d043b2b62e92860400be19eae212`.
This follow-up adds shutdown/claim-race protection, worker tooling-image CI and final setup/evidence.
Use the current PR head for the exact published documentation commit; no history was rewritten.

## Saved milestones

- `d3efcb7`: server-approved source scoping and pinned remote path mapping.
- `fd9273f`: bounded transport/staging, owner evidence UI and private publication reconciliation.
- `95bed12`: proxy inheritance rejection, serial browser verification and startup smoke.
- `34bfb83`: Linux-only rootless Podman/gVisor runtime, authenticated worker service, durable journal,
  pinned image and six-case opt-in isolation harness. Production owner dispatch remains disabled.

## Actual validation

[CI 41044345258](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/41044345258)
passed on `34bfb83`: 270 backend tests, six live-host skips, 94.02% statement coverage
(2,027/2,156), PostgreSQL integration, Ruff/format, mypy, TypeScript, 13 component tests,
six Chromium cases, private/public production builds, application container smoke and audits.
Local full suite: 265 passed, 11 skips, 93.37% (2,013/2,156). Four PostgreSQL and one symlink
case are local environment skips; six require a real isolated Linux host in both environments.
No new coverage exclusions. The lower percentage includes new Linux runtime/startup paths.

Follow-up shutdown/claim guards: 25 sandbox-controller tests passed; diagnostic test passed;
Ruff/format and mypy (27 source modules) passed. Current-head CI must also verify the newly added
trusted worker-image build/import smoke, which is explicitly not a hostile-code isolation test.

Four local Chromium tests passed serially, after an initial timeout under competing work; no
assertion or timeout was weakened. Two live HTTPS Pages desktop/mobile cases passed. Public
mobile and test-only owner screenshots were inspected. A real temporary owner factory process
passed health/authentication/logout HTTP checks with no external calls. Python/npm audits found
no known vulnerabilities and configured secret patterns found no matches. See
[evidence record](../evidence/v3-runtime-checks.json) and [evidence narrative](evidence.md).

## Exact remaining gates

1. No configured real model/API key or installed local model. Paid execution has no authorization.
2. No GitHub App installation/key; live installation-scoped operations remain unvalidated.
3. No suitable Linux worker, Podman or runsc in this Windows environment. The runtime exists but
   its effective isolation, resource enforcement and teardown have not run on a real host.
4. Owner `/execute` and private publication deliberately remain closed. After actual host evidence
   passes review, wire the existing WorkerDispatcher into that route; do not add a bypass switch.
5. Real-model → isolated verification → genuine private PR acceptance has not run. Issue #1 →
   draft PR #2 remains authentic deterministic fixture evidence, not a real-model result.
6. Private cloud is not deployed; Netlify stays pending by owner choice. No cloud resources or
   unrelated databases/repositories were changed. Local operation does not require paid hosting.

## Next executable action

Finish/check current PR CI, particularly the new tooling-image build, and record its result in PR #8.
Do not rerun/rebuild unchanged provider or worker contracts. With current external resources absent,
keep execution disabled. When the owner can supply them, follow the concrete
[activation checklist](activation-checklist.md), [Windows startup](local-owner-windows.md) and
[Linux worker setup/harness](linux-worker.md). Run `python -m repopilot.doctor` first; it prints
presence and platform status without credentials or network calls. Never paste secrets into chat.

Overall real-agent status: INCOMPLETE. No live model/App/sandbox or production-readiness claim.
No automatic merge, paid services, force push, unrelated fork or portfolio edit is authorized.
