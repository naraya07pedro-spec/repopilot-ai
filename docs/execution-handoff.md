# V3 integration checkpoint — 30 October 2026

Branch: `feat/v3-providers`; existing [PR #8](https://github.com/naraya07pedro-spec/repopilot-ai/pull/8), open/unmerged.
Last published source-scoping checkpoint: `d3efcb70c194eeae1aa15c14df65bf9f9a76209d`.
Its [CI 40991695569](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/40991695569) passed.
This checkpoint preserves the integration milestone; final full-suite/CI evidence follows.

## Newly completed independent work

- Bounded server-selected source roots bind request identity, approval, worker claim and remote patch paths.
- Temporary candidate text staging with snapshot checks and cleanup; no candidate execution/imports.
- Loopback-only signed HTTP job/cancellation transport, durable dispatch failure handling and no automatic retries.
- Separate publication approval, candidate/receipt binding, atomic claim, draft PR creation and read-only reconciliation.
  Lost acknowledgements and restart never trigger repeated writes or invented success.
- Owner API authorization/Origin checks, receipt and PR display, publication preview and reconciliation controls.
- Secret-free offline diagnostics and reproducible [Windows startup](local-owner-windows.md).

## Verified at this checkpoint

124 targeted GitHub App/owner/worker/transport/publication tests passed. Ruff check and format, mypy
(25 source modules), TypeScript, 13 frontend component tests and the production frontend build passed.
Secret-pattern and whitespace checks passed. Full-suite coverage, browser tests and new-head CI are pending.
All new GitHub responses and worker receipts are synthetic test data. One transport test uses a real
loopback HTTP server; it does not run repository code or prove isolation.

## Gates and next exact action

Owner explicitly cannot supply credentials, spending approval or a Linux worker. Do not ask again during
this continuation. No paid calls, cloud resources, unrelated repository writes or merges are authorized.
Execution and private publication remain closed through `DisabledWorker`, with no environment bypass.
No production dispatcher/runtime is wired into `/execute`. The transport and publisher are tested code;
they are not a working sandbox or a completed live coding agent.

Next: complete full backend coverage, four local Chromium cases, two live Pages cases, dependency audits,
and a credential-free owner HTTP startup smoke; publish results to PR #8 and inspect its current-head CI.
When a suitable Linux worker becomes available, implement/review the runtime binding, enforce and test
isolation/quotas/egress/cleanup, then wire the dispatcher. Only after server-side model and GitHub App
configuration (and paid consent where applicable) may a real model-to-PR acceptance run proceed.

External blockers: no model credential or installed local provider; no GitHub App installation/key;
no suitable isolated Linux worker. Private cloud remains undeployed; Netlify remains pending by owner
choice. Public Pages is unchanged. Overall real-agent delivery remains PARTIAL.

## Prior checkpoint (historical)

# Scoped-inspection recovery — 30 October 2026

Branch feat/v3-providers; existing PR #8. Recovered three unpublished scoped-inspection
files on top of 875ff38f75996ee408005aaab810007293ad5316. Prior head CI 40887290408 passed.
This checkpoint adds server-selected repository subdirectory inspection, immutable source-root
mapping and regression tests without changing provider/worker contracts or execution gates.
Targeted validation: 49 GitHub App/owner tests, Ruff check/format and mypy (22 modules) passed.
Credential-pattern scan and diff whitespace check passed. Full follow-up CI still needs checking.

Owner explicitly cannot provide credentials, worker infrastructure or spending approval.
Continue independent integration, local startup and deployment preparation only. Keep execution
and unverified publication disabled; no paid resources or calls, no automatic merge.
Next: bind source scope into queued request identity, harden scoped responses, implement/test
publication reconciliation and transport integration behind the existing closed worker gate.

## Prior verified checkpoint

# V3 verified continuation checkpoint — 29 October 2026

Branch: `feat/v3-providers`. Existing [PR #8](https://github.com/naraya07pedro-spec/repopilot-ai/pull/8)
is open and unmerged. Latest verified implementation commit:
`4d4768d7a34c07aeb9440d43edbfaa9be156f1a2`. This documentation commit follows it without
changing runtime code. Recovery checkpoint `3e49acf56a390f52b6b379d30decdba00bf2e949`
contains all eight interrupted files; `49a920f` adds the validated worker security corrections.
No resets, force pushes, automatic merges or unrelated repository writes occurred.

## Completed and verified

- Five provider wire adapters; explicit profile/model selection, paid consent, context/output
  budgets, shared spending reservations, usage validation, no fallback, expiry-bound approval.
- Owner authentication, repository allowlist/installation contracts, durable planning/history,
  cancellation, and unified diff preview before approval. No-op/oversized changes fail closed.
- Authenticated worker jobs/receipts, single atomic claim, exact-job replay protection, repository
  revocation and configuration rechecks, cancellation acknowledgements and restart recovery.
- Production execution remains disabled. No sandbox driver, job transport or private PR publisher
  is active. See [worker contract](worker-contract.md); receipt fixtures do not prove isolation.
- Repaired two null-filled Git references only after backing up bytes and verifying commit/reflog
  history. The backups are under the task's work/ directory. Git connectivity check passed.

## Actual validation

[Verify 40886579341](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/40886579341)
passed on `4d4768d`: **203 backend tests, 96.05% statement coverage** (1,555/1,619), 12 component
checks, six Chromium cases (four Pages/owner plus two root export), PostgreSQL regressions,
Docker Compose HTTP smoke, Ruff check/format, mypy (22 sources), TypeScript, production builds,
locked Python/full npm audits and configured credential-pattern scan.

Local: **198 passed, five skips, 95.24%** (1,542/1,619). Four skips require local PostgreSQL;
one requires Windows symlink privileges; all five ran in Linux CI. Worker suite: 38 passed.
Twelve component and four local Chromium tests passed. Two further Chromium tests passed against
https://naraya07pedro-spec.github.io/repopilot-ai/ at desktop/mobile sizes. The owner/mobile
screenshots were inspected; the corrected owner labels and real diff display were checked again.
Public recording tabs, actual diff/results, PR #2 link and absent private endpoints were verified.

The recovery checkpoint browser locator failed in CI and was fixed using the accessible combobox
role. No assertion was removed. Non-failing Starlette/Vite compatibility warnings remain. Dependency
audits found no known vulnerabilities; secret patterns found no matches, neither proves full security.
No live model or App authentication was performed. Synthetic provider/worker contract fixtures are
not substitutes for those gates. Evidence: [check record](../evidence/v3-worker-local-checks.json).

## Exact next engineering / owner actions

1. Review PR #8 and verify its current-head checks before any owner-approved merge. Do not create
   another PR or repeat provider/worker construction. The public demo remains on existing main.
2. Add bounded, server-approved source scoping for this repository's fixture directory before a
   live private planning task: the present whole-repository profile accepts <=8 source files and
   this repository exceeds it. Do not authorize a different repository implicitly.
3. Owner supplies server-side `GITHUB_APP_ID`, `GITHUB_INSTALLATION_ID`, mounted
   `GITHUB_APP_PRIVATE_KEY_FILE` and repository allowlist, plus a model profile and either an
   installed local endpoint or an API credential with explicit paid budget/consent. Never paste
   secrets into chat. These were all absent; no paid calls were made.
4. Implement a dispatcher/controller and separately reviewed disposable VM/microVM runtime with
   secret-free guest, network denial, quotas, cancellation/cleanup and adversarial tests. Docker,
   Ollama and installed WSL are unavailable locally. Keep `/execute` at 409 until independently
   verified. Signed-message tests and the application container smoke are not sandbox validation.
5. Connect exact candidate materialization, independent receipt verification and explicit PR write
   approval with remote baseline/uncertain-write reconciliation. The current publisher remains
   fixture-only. Run a genuine model-backed Issue-to-PR task only after these gates pass.

## Release status

Public demo: verified. Provider/owner/worker contracts: verified. Local real agent: PARTIAL.
Live model/App validation, runtime isolation and connected private publication: BLOCKED/incomplete.
Private cloud is not deployed; Netlify remains pending by owner decision. No infrastructure,
Supabase application data or portfolio repositories were modified. No full-product completion
or unattended continuation is claimed.

## Historical checkpoints

# Worker recovery checkpoint — 29 October 2026

Branch: feat/v3-providers; existing PR #8. Base published head a79d4a3cdcfac27bb7d8cfefbb5e33e0636821bf.
Recovered all eight unpublished worker/owner/frontend/test files. The branch reference
matches valid commit ba8d497 and its reflog; no working-tree or index reset was used.
The earlier damaged-reference backup remains outside the repository in work/.

Targeted validation at this checkpoint: 95 worker/provider/owner tests passed;
Ruff check and format passed; mypy passed (22 source files); tracked credential-pattern
scan passed (128 files). Full-suite and browser completion are still pending.
The new browser case previously timed out locating the Model selector; preserve and fix it.
Do not infer final CI or sandbox success from this recovery commit.

Implemented authenticated worker jobs and receipts, atomic claims, replay protection,
cancellation acknowledgement and interruption recovery. Production dispatch stays disabled.
Next exact action: fix the new owner browser selector, rerun frontend checks and Chromium,
finish worker security edge cases, run full checks and publish results to this same PR.
No provider/App credentials, Ollama, Docker or installed WSL were available. No paid calls,
new infrastructure, live model execution or independently verified sandbox is claimed.

## Previous provider handoff (historical)

# V3 implementation — 29 October 2026

Branch: feat/v3-providers. Published recovery checkpoint: b6e5316240833633f2df4e3862af01a1d1f0296b.
PR #7 is merged; base main is 68bf412d6451c7982509d7c5c0ca3ba27826db86. Do not reopen it.
Implemented five provider wire adapters, safe model registry/discovery, owner selector/budget/
paid consent, immutable selection in idempotency/approval, and one-hour approval expiry.
The deterministic provider and public viewer are unchanged. No automatic fallback exists.

Fresh local results: 158 backend tests passed, five environment skips, 94.84% coverage;
33 new provider tests include an actual unavailable loopback endpoint, not a live model.
Ruff/mypy passed. Twelve component tests, TypeScript, owner/public production builds and
both dependency audits passed. A small UI retry-consent change is awaiting its affected rerun.
The final review PR/checks will be linked below after publication; do not infer CI success.

Next executable steps: finish frontend rerun and browser checks; publish reviewed provider
implementation; implement/test the disabled worker interface and receipt lifecycle if runtime
isolation remains unavailable. No Docker/Ollama executables or installed WSL were found.
No API/App credentials exist here. No real-model, hostile-code worker or private-cloud result
is claimed. Keep /execute at 409 and the exact-byte fixture gate intact. Netlify stays on hold.

## Recovered WIP checkpoint

Active branch: feat/v3-providers, based on merged PR #7 at 68bf412.
Recovered eight modified/new provider, owner UI and test files. This checkpoint is WIP:
30 existing owner tests and mypy passed before interruption, but new adapter contracts,
model discovery proxy routing and complete UI validation remain unfinished.
Do not merge this checkpoint or enable arbitrary code execution.
Next: preserve provider PolicyError classifications, allow the bounded model-discovery
proxy route, add provider/selection/budget/approval regressions, then run full checks.
No provider/App credentials, Ollama, Docker or installed WSL were available at recovery.
No paid calls or new infrastructure are authorized. The public Pages demo stays unchanged.
The V3 request supersedes the earlier development deferral; spending remains default-deny.

## Earlier portfolio handoff — 29 October 2026

Current scope: zero-additional-cost public portfolio release. Preserve the working Pages site.
Do not expand private infrastructure, provision resources, call a paid model or resume Netlify
publication; the owner deferred those activities.

Branch: `feat/hosting-readiness`. Existing review PR: #7 (reuse it).
Verified implementation commit: `06a7171cf43f8063f58b6f59c6bea21effa41f3e`.
The release documentation follows that commit; inspect the current PR head before continuing.
The recovered 22 files were committed locally in 8a796ac; the remaining five-file correction
was published in 7286e55. CI exposed a schema-owner REVOKE failure, fixed in 06a7171 without
relaxing NOINHERIT or the regression test. Local and API metadata histories were preserved.

Verified CI: 40812511056 — 130 backend tests, 95.69% coverage, 10 component tests, 5 browser
cases, PostgreSQL bootstrap/recovery, Docker smoke, lint/types/builds/audits/secret scan passed.
Local: 125 passed, 5 environment skips, 94.59%; 10 frontend tests, 3 local browser cases,
2 browser cases against the live HTTPS site, TypeScript/builds/audits passed.
Coverage scope and exact evidence links are in docs/evidence.md. Public URL:
https://naraya07pedro-spec.github.io/repopilot-ai/ (verified 29 October).

Next executable action: inspect PR #7 and checks on its current head; integrate only after
review and green CI, then verify main CI/Pages. If already merged, do not recreate the PR.
No forced history changes or automatic merge of demonstration draft PR #2.

Private V2 remains PARTIAL: no live App/model result, production database connection or private
HTTPS host. A validated isolated worker is not implemented; private execution remains 409.
The final SQL regression ran on disposable CI PostgreSQL. No existing Supabase data changed.
Netlify stays pending by owner decision. These are explicitly deferred expansion gates;
credentials alone do not supply a secure worker. No new spending is authorized.

## Historical handoff — 28 October 2026

The following records prior context. Its expansion steps are superseded by the scope above.

Overall status: PARTIAL. Public recruiter demo: DEPLOYED AND VERIFIED.
Public URL: https://naraya07pedro-spec.github.io/repopilot-ai/

## Published state

V2 PR #4 merged normally into main at 1e79482783675c0b74a980e5cb2714442b66b978 after
fresh green CI and review of public/private separation. PR #5 introduced an incompatible
root-level Next.js workflow; the owner deleted it in 71f5002. That deletion is preserved.
Only public-demo.yml publishes, only from main. No reset, force-push or unrelated repo changes.
Actual fixture Issue #1 -> draft PR #2 remains separate and unmerged.

Documentation PR #6 merged at c64c0cf548039725f1c53c155c98630198780f6a with green Verify
40639976253 and Pages 40639976294 (including two live Chromium tests).
Current development branch: feat/hosting-readiness, based on that main commit.
Inspect current git status/log and PRs before resuming. Local/API commit metadata may differ;
publication verifies exact tree equality. Never rewrite histories to reconcile metadata.

## Hosting preparation continuation

The owner selected Netlify for the public export and an accessible existing Supabase project
for PostgreSQL; no paid provisioning is authorized. The intended Netlify account is not the
working connected account, and the owner explicitly asked to keep its deployment pending.
An active Supabase project has other applications' tables. Only their metadata was inspected.
A rollback-only bootstrap/probe validated creating and using the new restricted role/schema;
a separate query confirmed neither object remained. No existing data or global settings changed.

Prepared netlify.toml for the root-path static export, deploy/render-preview.yaml with two
free control-plane web services (no database/worker), and exact external steps in
docs/hosting-setup.md. No resources are provisioned by those files alone.
Production/Supabase startup now requires a private PostgreSQL schema and verified TLS.
Private-schema migrations revoke public/browser-role access and enable RLS. Added a real
PostgreSQL restricted-role, schema-isolation and restart-recovery test for CI.

Local checks so far: 124 backend tests passed, 4 environment skips (three PostgreSQL, one
Windows symlink), 94.42% statement coverage; affected database/owner checks 43 passed.
Ruff, formatting and mypy passed. Frontend: 10 tests, TypeScript, owner production build and
root-path public production build passed. Render configuration passed the official JSON
schema; Netlify TOML parsed. Three actual local Chromium tests passed (root-path public demo
at desktop/mobile sizes and private owner login/logout/disabled execution). Both dependency
audits found no known vulnerabilities; the tracked-file credential-pattern scan passed.
PR #7 publishes this stage. Verify run 40652011337 at 296bae7e8ef7c7cdd9506453b9121b4b7f4c2658
passed 128 backend tests with 95.69% coverage, including the restricted PostgreSQL role,
RLS/private schema and recovery test. Frontend passed 10 component tests and 5 browser flows
(Pages/owner 3, root-path public 2); container smoke and audits passed.
A final hostname-normalization regression adds coverage for uppercase/trailing-dot Supabase
hosts; its 14 database configuration tests passed locally. Check CI on the updated PR head
before integrating, rather than using an older green run as approval.
Supabase's non-superuser administrator required explicit SET membership in the newly created
role. The bootstrap now grants that membership without INHERIT and a new PostgreSQL regression
test exercises the real bootstrap script under a non-superuser role. The corrected Supabase
transactional probe passed and was rolled back; no persistent DB installation is claimed.

## Actual verification

Main Verify 40639065402: 114 backend tests, 95.57% statement coverage, 10 component tests,
3 Chromium E2E tests, Ruff/mypy, TypeScript, production builds, PostgreSQL migration/session
recovery, Docker HTTP smoke, locked Python/full npm audits and secret-pattern scan passed.
Deployment 40639065386: public build/deploy passed; 2 additional Chromium flows passed against
the actual HTTPS site at desktop/mobile widths. Artifact 12794941485 has live screenshots.
Independent HTTPS checks saved in evidence/public-https.json: homepage 200, 8 assets 200,
owner/API routes 404. Earlier Pages 404 reports are historical and resolved.

## Remaining blockers and implementation gaps

Owner sessions, App installation scoping, real-model planning adapter, budget reservations,
approval binding, idempotency, cancellation and recovery are implemented and contract-tested.
Live GitHub App and real-model calls are unverified: no App ID/installation/key, model API key,
authorized spending limits or production DATABASE_URL are configured in the current environment.
No secrets have been requested in chat or added to the public site.

A validated isolated worker is NOT implemented or provisioned. General private modifications,
verification and PR publication remain disabled (409). Docker is absent locally; CI Docker
smoke is not evidence of a hostile-code sandbox. Do not remove the exact-byte host fixture gate.
No private HTTPS deployment, production recovery, comprehensive accessibility or adversarial
sandbox review is claimed. A Netlify connection is now reachable, but the intended hosting
account connection is incorrect for the requested target; publication stays pending by owner
request. Render is an evaluated free preview option; no hosting resource was created.

## Next exact actions

1. Check the latest head of PR #7 and finish review/integration if still open, then verify
   main CI/Pages. Preserve the working Pages host and Netlify publication hold.
2. Follow docs/hosting-setup.md: reconnect the intended Netlify account when the owner resumes
   publication; bootstrap only a private Supabase schema/role in the selected existing project,
   inject its verified-TLS connection secret, and connect an approved container hosting account.
   Configure App/model server-only variables and explicit spending limits; never paste keys in chat.
3. Implement and validate a disposable secret-free VM/microVM worker with denied network,
   filesystem/resource/time limits, cancellation, cleanup and immutable evidence transfer.
   Keep private execution closed until this review passes.
4. Validate real App/model planning on an explicitly authorized small repository, then bounded
   edits, independent verification and reconciled PR publication with human approval.
5. Deploy the private control plane behind HTTPS with PostgreSQL/backups and test actual recovery.

The existing small-repository inspection profile is limited to 8 source files / 24 KB total;
this project exceeds it. A future live private task must use an explicitly approved compatible
repository or a separately reviewed scoped-inspection enhancement. Do not create a new repo
or access unrelated repositories merely to satisfy that test.
