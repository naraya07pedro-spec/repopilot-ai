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

## Validation checkpoint

Before release-specific changes: 141 selected provider/owner/transport/publication contract tests
passed locally. Ruff/format/mypy, full backend coverage, frontend checks/builds/browser and current
GitHub CI must be measured on this new branch and recorded before claiming release readiness.
Historical PR #8 test counts are not this release's counts. No live provider or App validation
is available. Public Pages and Issue #1 → draft PR #2 remain deterministic recording evidence.

## Remaining blockers and next action

Finish the current release checks and review PR, retain its exact source commit and CI links.
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
