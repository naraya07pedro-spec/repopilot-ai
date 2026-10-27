# Verified execution evidence

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
