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
