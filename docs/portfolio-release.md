# Application portfolio release boundary

This release is the public recorded demonstration plus a single-owner planning/review control
plane. It is independently reviewable against `main`; it is not the completed real coding agent.

## Included and fail-closed

- Existing public GitHub Pages recordings, authentic Issue #1 / draft PR #2 and actual fixture tests.
- Five explicit model adapters and selection, validated plan/edit responses, context limits,
  server-side credentials, per-run paid-call consent and bounded spending reservations.
- Owner authentication/expiry, repository/source-root scoping, candidate preview, exact approval,
  durable history, cancellation states and truthful connection failures.
- Signed worker job/receipt contracts, loopback transport and publication reconciliation, all
  contract-tested. The owner uses `DisabledWorker`; execution and private publication reject
  requests. No runtime enable switch exists. Fixture execution remains limited to audited bytes.
- Windows setup/diagnostics, PostgreSQL integration and the existing application CI checks.

The model adapters and GitHub App have not been exercised with live credentials. Synthetic
receipt/provider tests do not prove model quality, remote writes or OS isolation.

## Preserved experimental scope

[PR #8](https://github.com/naraya07pedro-spec/repopilot-ai/pull/8), branch `feat/v3-providers`, is
preserved at `37c01e9c6bb77b75940f4072aa8cf0974a8d8b37`. It retains the Linux driver, worker
server, image/bootstrap, harness, controller tests, all six live security probes, and raw linked
failure evidence. Its mandatory sandbox job remains failed. Do not merge that PR wholesale.

This branch starts from `main` (`68bf412`) and copies the application file set identified at
`95bed12`, using preserved V3 source bytes from `37c01e9`. It adds release documentation.
The experimental runtime files never enter this branch; no test or workflow is deleted relative
to `main`. `.github/workflows/verify.yml` remains byte-identical to `main`. Its passing results
apply to the application scope only, and cannot supersede PR #8's failed isolation gate.

[Immutable failed sandbox run](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/41161973178) ·
[Systemd/cgroupfs diagnosis](https://github.com/naraya07pedro-spec/repopilot-ai/blob/37c01e9c6bb77b75940f4072aa8cf0974a8d8b37/docs/sandbox-ci-diagnosis.md).

## Release acceptance

Require green application CI, both production builds, browser flows including denied private
execution, dependency/secret-pattern checks, and verified public HTTPS recordings. Record the
actual new-branch results in evidence.md and the handoff. Never reuse the larger PR #8 test count
as this release's result. No automatic merge, tag, Pages publication or private deployment occurs.

## Exact remaining real-agent gate

Supply and review a compatible runtime/test host before further implementation experiments.
Independently pass resource/network/filesystem tests, running cancellation, cleanup and recovery.
Only then review the owner dispatcher binding and run one authorized real model/App task through
actual isolated tests to a draft PR, including duplicate-write reconciliation. Model credentials,
GitHub App credentials and paid-call authorization remain absent. See
[owner activation](owner-activation.md) and [runtime options](runtime-options.md).
