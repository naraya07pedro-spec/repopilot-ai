# Verified execution evidence

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

V2 remains PARTIAL. Pages reports site-not-found and the intended HTTPS URL returned 404 even
after the owner reported saving Actions source. Private execution/PR publication remains closed
pending a validated isolated worker. App credentials, model credentials/approved spend and
private hosting were unavailable. Native Computer Use stopped because it could not determine
the current browser URL confidently; no safety guard was bypassed.

The historical V1 evidence below remains valid for its stated commit and date. Its browser
limitation is superseded by the CI browser results above; hosted URL verification is still open.

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
