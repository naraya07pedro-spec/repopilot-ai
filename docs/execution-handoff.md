# V3 recovery checkpoint — 29 October 2026

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
