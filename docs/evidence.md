# Application release evidence — 31 October 2026

[PR #9](https://github.com/naraya07pedro-spec/repopilot-ai/pull/9) separates the fail-closed
application from PR #8. [CI 41165328471](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/41165328471)
passed on `b611e8272e4318c981006ce4db239f3dd97ee647`: **247 backend tests, zero skips,
96.10% coverage** (1,801/1,874), PostgreSQL, Ruff/format, mypy (25 sources), 13 component tests,
six Chromium cases, private/public production builds, container smoke and dependency audits.
The configured credential-pattern scan checked 141 tracked files without matches.

Local full backend: **242 passed, five environment skips, 95.36%** (1,787/1,874). Four cases need
PostgreSQL; one needs Windows symlink privilege. All run in Linux CI. No new coverage exclusions.
TypeScript, 13 component tests, private/public builds and four serial Chromium tests passed.
Two additional live HTTPS Chromium tests passed at desktop/mobile sizes, inspecting recordings,
actual diff/test/PR evidence, rejected regression and denied private endpoints. The actual mobile
screenshot was visually inspected. The public URL remains https://naraya07pedro-spec.github.io/repopilot-ai/.

The approved-plan API regression confirms private execution/publication remains denied.
All sandbox files and six failed live probes remain preserved in
[PR #8's failed run](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/41161973178).
This branch never contained that runtime; its CI workflow is identical to main and no tests or
workflows are deleted relative to main. Application success does not supersede the isolation failure.
No live model, App installation or real-agent Issue-to-PR acceptance was run.
[Structured release record](../evidence/v3-portfolio-release-checks-2026-10-31.json) · [Release boundary](portfolio-release.md).

## Historical evidence

# Verified execution evidence

## Final V3 implementation verification — 29 October 2026

[Verify 40886579341](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/40886579341)
passed on `4d4768d7a34c07aeb9440d43edbfaa9be156f1a2`: **203 backend tests, no skips, 96.05%
statement coverage** (1,555/1,619). Twelve component tests, six Chromium cases, PostgreSQL
integration, container HTTP smoke, TypeScript, production builds, Ruff/mypy and dependency audits
passed. The new private diff preview is verified before approval, including no-op/oversize rejection.
No live model/App or sandbox execution occurred. Public demo checks passed separately as below.
The [handoff](execution-handoff.md) identifies remaining runtime engineering and credential gates.

## Earlier V3 worker checkpoint — 29 October 2026

Recovery commit `3e49acf56a390f52b6b379d30decdba00bf2e949` preserves the eight interrupted
files in [PR #8](https://github.com/naraya07pedro-spec/repopilot-ai/pull/8). Its backend and
container jobs passed; its browser job exposed the existing Model label lookup failure.
The corrected accessible-role locator passes the actual owner workflow locally.

[Fresh local check record](../evidence/v3-worker-local-checks.json): **198 backend passed,
5 environment skips, 95.24% coverage** (1,542/1,619 statements). Worker contracts: 38 passed. The later diff preview adds no-op/oversize and new-file/newline
regressions and a browser assertion before approval.
Twelve component tests, four local Chromium cases, Ruff lint/format, mypy (22 sources),
TypeScript, owner/Pages production builds and locked Python/full npm audits passed.
The five local skips are four PostgreSQL cases and one Windows symlink privilege case.
No coverage exclusions were added. [Follow-up Verify 40885395485](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/40885395485)
passed at `49a920fa87789413117448ad1ead382adf37fe19`: **201 backend tests, 96.02% coverage**
(1,544/1,608 statements), 12 component tests, six Chromium cases (Pages/owner: four; root: two),
PostgreSQL checks, Docker Compose smoke, lint/types/builds and dependency audits.
Two additional local Chromium cases passed against the deployed HTTPS site at 1440px/390px.
The live mobile screenshot and test-only owner screenshot were visually inspected; two garbled
owner labels were found and corrected. The owner screenshot is synthetic test data, not live AI.

Worker receipts and provider responses are synthetic contract fixtures. No live model,
GitHub App credential validation, hostile-code sandbox or private PR publication ran.
The authenticated protocol does not prove execution isolation; dispatch remains disabled.


## Portfolio release verification — 29 October 2026

[PR #7](https://github.com/naraya07pedro-spec/repopilot-ai/pull/7) preserves the interrupted
hosting work and completes its non-superuser bootstrap correction. All 22 recovered files
were already committed locally; the final five-file correction had not been published.
No existing Supabase application data was changed and no infrastructure was provisioned.

[Verify 40812511056](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/40812511056)
at `06a7171cf43f8063f58b6f59c6bea21effa41f3e` passed all three jobs:

- Backend: **130 passed, no skips; 95.69% statement coverage** (1,132/1,183 statements).
  Scope is `repopilot/`, excluding the existing CLI wrapper; no new coverage exclusions.
  Real disposable PostgreSQL 17 tests cover non-superuser bootstrap, private schema/RLS,
  concurrent idempotency, sessions and restart recovery.
- Frontend: **10 component tests and 5 Chromium cases** (Pages/owner: 3; domain root: 2).
  TypeScript, owner build and both static base-path builds passed.
- Ruff lint/format, mypy (19 sources), locked Python/full npm audits, secret-pattern scan
  and Docker Compose HTTP smoke passed. Audits found no known dependency vulnerabilities.

[Earlier run 40812060958](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/40812060958)
correctly failed the new bootstrap regression: SET membership without INHERIT did not let the
administrator revoke schema privileges as its owner. The script now uses SET LOCAL ROLE for
that operation. The restricted role remains NOLOGIN, NOINHERIT and without elevated privileges;
the regression assertions and execution restrictions were retained.

Windows rerun: **125 passed, 5 skipped; 94.59%** (1,119/1,183 statements). Four PostgreSQL cases
require the absent local server; one symlink test needs Windows privileges. All five ran in CI.
Local Ruff/mypy, 10 component tests, TypeScript, owner/root public builds and audits passed.
Three local Chromium cases passed, including actual owner login/logout, CSRF rejection and
disabled-execution controls against a temporary backend with test-only credentials.

Two additional Chromium tests passed against the deployed HTTPS site at 1440px and 390px:
actual diff, passing tests, PR #2 link, rejected regression, recording labels, absent private
routes, no API requests, no JS errors or failed assets, and no horizontal overflow.
The mobile screenshot was visually inspected. [Fresh HTTP record](../evidence/public-https-2026-10-29.json)
independently confirms homepage/eight assets 200 and owner/API paths 404.

This release is the public portfolio demonstration. Netlify remains on hold by owner decision;
paid-model validation, GitHub App live credentials, production private hosting and a reviewed
isolated worker are deferred. The final bootstrap ran on disposable CI PostgreSQL, not as a
persistent Supabase installation. Earlier rollback-only Supabase evidence remains limited to
its stated probe. No live model, private execution readiness or production deployment is claimed.

## Public release — 28 October 2026

The [public demo](https://naraya07pedro-spec.github.io/repopilot-ai/) is live and verified.
PR #4 merged normally at 1e79482783675c0b74a980e5cb2714442b66b978 after fresh green
checks and review of public/private separation. PR #5's generic workflow had already been
deleted by the owner in 71f5002; its deletion was preserved. Only the correct public-demo
workflow publishes from main. Demonstration PR #2 remains separate and unmerged.

[Main Verify](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/40639065402)
passed: 114 backend tests, 95.57% coverage, 10 component tests, 3 local Chromium E2E tests,
PostgreSQL recovery/migrations, Docker smoke, lint/type/build checks and dependency audits.
[Public deployment](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/40639065386)
also passed 2 Chromium tests against the deployed HTTPS URL at 1440px and 390px. These
exercised evidence tabs, actual diff/test text, the PR #2 link, rejected regression, no public
API calls, no browser exceptions and no horizontal overflow. Artifact: 12794941485.

[Independent HTTPS checks](../evidence/public-https.json) recorded homepage 200, eight
script/style assets 200, and /owner/, /api/owner/settings and /api/demo/runs all 404.
No token, login or payment was used. The website displays recorded deterministic fixture runs;
its availability does not establish live model execution or private execution readiness.
The earlier Pages errors below are preserved historical evidence and are now resolved.

## V2 verification — 28 October 2026

[CI 40609756593](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/40609756593)
passed at `61c38f154900b59fad569457555b5612db9103ad`: 114 backend tests, 95.57% statement
coverage, 10 component tests, 3 actual Chromium end-to-end tests, TypeScript, owner/static
production builds, PostgreSQL migration/session/recovery tests and Docker HTTP smoke.
Ruff, mypy, full npm audit, locked Python audit and the configured secret-pattern scan passed.
Audit results mean no known vulnerabilities found, not proof of complete security.

Browser cases exercised the public evidence tabs at 1440px and 390px, checked no public API
calls, and exercised owner login/logout, unauthorized access and unavailable-execution controls.
They ran against production builds with an actual temporary FastAPI server and synthetic
credentials. No live App/model calls were made. Scope excludes a full accessibility audit.

[Release check record](../evidence/v2-release-checks.json) contains commit/job identifiers.
[Desktop](images/public-desktop.png) and [mobile](images/public-mobile.png) screenshots came
from artifact 12781912494 in run 40608844672; public code is unchanged by the later proxy fix.
They show a genuine rejected-regression view and were visually inspected.

Recovered local full suite: 110 passed, 2 environment skips, 95.61% coverage. These earlier
measurements remain in v2-local-tests.xml/v2-local-coverage.json. Subsequent affected reruns
passed 41 owner/App tests and 3 API tests. Ten component tests, TypeScript, production build
and local dependency audits passed. Final CI includes the newer PostgreSQL/cancellation cases.

Resolved defects: missing container build-context evidence; provider PolicyError misclassification;
cancellation overwriting a newly completed plan; and a proxy Origin mismatch caused by Next.js
URL normalization. The proxy now uses the configured external origin; CSRF rejection remains
tested. The failed browser trace was retained and the corrected real-browser run passed.
One Windows API test exceeded its polling window during concurrent builds; an isolated rerun
passed without changing its assertions or timeout.

At that earlier checkpoint V2 remained PARTIAL. Pages reported site-not-found and the intended HTTPS URL returned 404 even
after the owner reported saving Actions source. Private execution/PR publication remains closed
pending a validated isolated worker. App credentials, model credentials/approved spend and
private hosting were unavailable. Native Computer Use stopped because it could not determine
the current browser URL confidently; no safety guard was bypassed.

The historical V1 evidence below remains valid for its stated commit and date. Its browser
limitation and hosted-URL blocker are superseded by the later public-release verification above.

Recorded on 27 October 2026. This is a working, fixture-bounded reference implementation.
General repository execution, live model quality and production readiness are not claimed.

## Real GitHub issue to pull request

- Issue: https://github.com/naraya07pedro-spec/repopilot-ai/issues/1
- Engine-generated draft PR: https://github.com/naraya07pedro-spec/repopilot-ai/pull/2
- Pinned remote baseline: `62ffdfe2541e05a05a9b1e6f5691da41f5034552`
- Published candidate: `6753474ea24d28996d48b40fe7c8efb9a6b454eb`
- Local engine candidate: `c9f4340b48199971dbf5d842ecbc8ee60ad9d507`
- Run: `e299ad71ce264698b593615d2b3971c4`
- Artifact SHA-256 digest: `10af6c28acdac312412712bde779d17060e91636686d4f1982f47115136b118b`

The actual CLI fetched the public issue and immutable repository files through the application's
GitHub adapter. The engine inspected the files, ran baseline tests, validated the bounded plan,
applied the authorized catalog edit, ran candidate pytest/lint/format checks, and committed.
The connected GitHub integration published the exact digest-validated artifact without exporting
credentials. GitHub's PR files endpoint independently confirmed one changed line in
`fixtures/bug/app.py`: floor division became true division. No merge was performed.

This proves live GitHub ingestion and connector-assisted publication. It does not prove a live
invocation of the application's token-based publisher or a paid AI provider. The deterministic
provider is explicitly labeled. These are seeded fixtures, not customer repositories.

[Full live record](../evidence/live-bug.json) · [PR artifact](../evidence/live-bug.pr.json) ·
[Publication verification](../evidence/github-publication.json)

## Actual scenarios

| Scenario | Baseline pytest | Candidate pytest | Result |
| --- | --- | --- | --- |
| [Live bug](../evidence/live-bug.json) | 2 failed, 1 passed | 3 passed; lint/format exit 0 | Verified; real PR #2 |
| [Feature](../evidence/feature.json) | 1 passed | 3 passed; lint/format exit 0 | Verified; offline PR artifact |
| [Regression](../evidence/failure.json) | 2 failed, 1 passed | 2 failed, 1 passed | verification_failed; exit 1; no commit or PR |

## Quality verification

[GitHub Actions run 40492779772](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/40492779772)
passed backend, frontend and container jobs at the pinned baseline above.

- Linux backend: **72 passed**, **95.68% statement coverage**; PostgreSQL and symlink cases ran.
- Windows backend after pytest 9.0.3 upgrade: **70 passed, 2 skipped**, **95.52%**.
  Local skips: PostgreSQL unavailable and Windows symlink creation privilege.
- Ruff lint and formatting passed; mypy passed all 12 application source files.
- Frontend: **4 tests passed**, TypeScript and production build passed locally and in CI.
- Production dependency audit: zero known vulnerabilities. Python locked-dependency audit passed in CI.
- Docker Compose build/start and backend/frontend HTTP health checks passed in CI. Docker is absent locally.
- [Production HTTP smoke](../evidence/http-smoke.json): homepage, headers, idempotency, approval
  digest rejection/acceptance, genuine execution, saved history and cross-origin rejection passed.
  Reproduce with `python scripts/smoke_http.py` while both local production services are running.
- Tracked-source pattern secret scanning passed. This is not exhaustive secret detection.

See [testing](testing.md) for exact scope/exclusions. Coverage excludes the CLI wrapper, tests,
fixtures, dependencies and frontend. Saved local coverage/JUnit files are actual measurements.
The console replay is an exact copy of the saved live run and is labeled as a replay.

## Failures retained and resolved

- [First live attempt](../evidence/live-attempt-1.json) failed with `remote_fixture_not_audited`:
  the publication transport converted LF to CRLF. The byte gate was preserved. Publication was
  corrected, the remote tree was matched to local committed bytes, and the genuine run was repeated.
- Initial CI [40490773753](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/40490773753)
  failed the Python audit for pytest 8.4.2 (PYSEC-2026-1845). Upgrading to 9.0.3 resolved it.
- Windows pytest initially could not create its sandbox temp directory. A fresh short workspace
  `--basetemp` allowed the complete suite to run; no assertion was weakened.
- A stale local Next.js build directory caused EPERM. A fresh `REPOPILOT_BUILD_DIR=.next-verify`
  completed the production build. The default remains `.next`.
- Reviewing CI's install output exposed development-only Vitest dependency advisories beyond the
  production audit. Vitest was upgraded to 5.0.5; npm reported zero known vulnerabilities
  across the full installed dependency tree. CI now requires the full npm audit.

## Limits and permissions

Browser visual QA remains blocked: the supported browser-control tool timed out attaching its
webview. No screenshot or browser-interaction success is fabricated. Automated component tests,
production builds and real HTTP workflow checks provide separate evidence, not visual coverage.
No public deployment was created.

The authenticated account is naraya07pedro-spec. The original default branch commit
`c93e6755b21f801dbb1cdc963cd3f018f86970c6` is preserved. Branch-protection access returned HTTP 403;
the integration lacks administration permission. No other portfolio repository was modified.
# Hosting preparation evidence — 28 October 2026

[PR #7](https://github.com/naraya07pedro-spec/repopilot-ai/pull/7), revision
`296bae7e8ef7c7cdd9506453b9121b4b7f4c2658`, passed
[Verify 40652011337](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/40652011337):
128 backend tests, 95.69% statement coverage, 10 component tests and five local Chromium flows
across Pages/owner and domain-root public exports. The PostgreSQL service exercised a
restricted role, schema isolation, public-access revocation, RLS, sessions and restart recovery.
Container smoke and dependency audits passed. These are CI database results, not a live
Supabase deployment.

Windows local execution passed 124 backend tests with four environmental skips and 94.42%
coverage, plus three actual Chromium flows against the domain-root export and owner app.
Both production builds, TypeScript, Ruff/mypy, ten frontend tests and dependency audits passed.
The optional Render configuration matched its official JSON schema. Netlify publication is
pending by owner request; no paid resource or remote database change was made.
The bootstrap was also checked against the connected Supabase service in a rolled-back
transaction. Initial missing SET membership failed correctly; the corrected script let the
restricted role create a probe table, write/read one row and enable RLS. A separate query
confirmed role/schema absence afterward. This is live SQL setup evidence, not an application
connection, persisted deployment or model-execution result.
See [hosting setup](hosting-setup.md) for the remaining external actions and worker gap.
