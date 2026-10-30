# Current checkpoint — sandbox blocked by released runtime integration

Branch `feat/v3-providers`; [PR #8](https://github.com/naraya07pedro-spec/repopilot-ai/pull/8)
is open, unmerged and **not ready for integration**. Latest runtime correction:
`0c3ae880dea735f2cd083a3170efd40d9217f5e5`. The current PR head adds the diagnosis/evidence below.

[Full CI 41090628500](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/41090628500):
backend/frontend/container passed; **all six actual Linux probes failed, none skipped**.
Container create and configuration inspection succeed. Startup exits 125 with
`creating container: systemd error: Interactive authentication required.`
Released gVisor `release-20261026.0` uses system-wide systemd for rootless Podman 4.9.3;
[upstream #11543](https://github.com/google/gvisor/issues/11543) reproduces this and
[fix #13853](https://github.com/google/gvisor/pull/13853) is still open/unmerged.
This is a specific runtime/host incompatibility, not a generic absence of cgroup v2 in Actions.

Saved corrections: bounded/redacted diagnostics; canonical exact image ID; supported tmpfs
options with private non-root 0700 staging; exact configured runsc path recognition. No security
assertion, resource cap or execution boundary was weakened. No provider/frontend features added.

Actual checks: 28 local controller tests passed; full local backend at ea86ad0 was 268 passed,
11 environment skips, 93.42%. Current runtime CI: 275 backend passed, six separate-job skips,
94.03% (2,046/2,176); PostgreSQL, Ruff/format, mypy, 13 frontend tests, six Chromium cases,
TypeScript, public/private builds, container smoke and dependency/secret-pattern audits passed.
CI overall remains FAILED. See [exact six outcomes and host reproduction](sandbox-ci-diagnosis.md)
and [structured evidence](../evidence/sandbox-ci-diagnosis.json).

**Next exact action:** validate a reviewed upstream runtime release/configuration that supports
rootless user-systemd cgroups on a disposable host, then rerun the unchanged six-probe harness
and full CI. Do not use ignore-cgroups, rootful/privileged execution, broader polkit permission,
an unreviewed runtime fork, or skips. A different Linux host alone does not fix this version bug.

Activation still needs a validated worker host/runtime, a configured real model (or installed local
model; paid calls still unauthorized), and a repository-scoped GitHub App installation/key.
Owner dispatch/publication remain deliberately unwired/disabled. After host evidence review,
the remaining engineering step is the dispatcher binding and real Issue-to-PR acceptance run.
Neither live model/App use nor running-sandbox recovery has been demonstrated. No cloud was
provisioned, no unrelated repo was modified, and no merge occurred. Public Pages is unchanged.

## Earlier diagnostic checkpoints (historical)

# Podman tmpfs compatibility correction — 30 October 2026

CI 41090255712 on `aac5a2164abbc33d9b4cb5f86205cb010ab4db47` identifies the next
driver defect: Podman reports OCIRuntime as the configured absolute `/usr/local/bin/runsc`,
not the alias `runsc`. All other inspected controls matched. Accept only that exact configured
path or the existing alias; reject other paths/runtimes. Live assertions now show the already
bounded/redacted command evidence when execution fails. No assertion or limit was removed.

Correction published as `ea86ad067fad416fb7c3e20fceac3c6cf08a3238`.
CI 41089848261 now creates containers successfully but fails the effective-configuration check
before starting candidate code. This follow-up reports only the bounded checked settings,
excluding environment and mount paths, so the next correction can use the actual mismatch.
Full local suite at ea86ad0: 268 passed, 11 environment skips, 93.42% (2,031/2,174).

Diagnostic commit `5b00c77c6ed9b41fc215379be072d530454126b0` is published.
[CI 41088871352](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/41088871352):
backend, frontend and container passed. All six live probes failed at Podman create, exit 125:
`Error: unknown mount option "uid=65532": invalid mount option` (Podman 4.9.3).
This is a driver compatibility defect, not evidence of unavailable host isolation.

The correction uses supported bounded sticky tmpfs mounts. The non-root guest creates its own
private 0700 candidate directory; the live boundary probe now asserts its owner and mode.
Rootless runsc, resource limits, read-only image, no host mounts and no network remain enforced.
Local validation: 26 controller tests passed; Ruff, formatting and mypy passed. Next: inspect
all six real probes and the full CI suite on this correction. Owner dispatch stays disabled;
no live isolation or real-model acceptance success is claimed before those checks execute.

# CI diagnostic follow-up — 30 October 2026

Image-ID correction published as 6857df3903b8b1b871366a75168a5825b461929f.
CI 41087651221: backend/frontend/container passed; all six live probes now reach Podman create
and fail with sandbox_create_failed. Rootless/cgroup/image preflight passed. The prior generic
exception discarded the actual Podman stderr; this change adds bounded redacted exit/stderr
reporting, tested locally. Do not guess or relax the isolation configuration.
Next: inspect the sandbox job at this head for the exact creation failure, fix its verified cause,
and rerun all six probes/full CI. Owner execution stays disabled.

# Live CI probe correction — 30 October 2026

CI 41046517451 installed gVisor and built the image successfully. All six isolation cases stopped
before execution because Podman returns a bare 64-digit image ID while the driver expected its
sha256: prefix. The driver now canonicalizes the exact 64-digit digest; mutable tags remain denied.
Local sandbox-controller suite: 25 passed. Next: inspect the rerun on this new head; keep owner
execution disabled. No model/App credentials or deployed worker have been supplied.

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
