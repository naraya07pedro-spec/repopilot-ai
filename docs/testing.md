# Testing

Use README commands. pytest engine tests run real Git and real test subprocesses over
audited fixtures. httpx MockTransport tests establish adapter contracts, not live integrations.

Coverage includes all repopilot modules except cli.py (argument parsing/printing wrapper).
The CLI is exercised by recorded demo commands. Tests, frontend, fixture source and dependencies
are outside backend statement coverage. Threshold: 85%; see evidence for measured values.

Behavioral scope: baseline failure and repair; feature tests; failed candidate; authentication;
private/demo separation; concurrent idempotency/claims; approval binding; cancellation/restart;
traversal; secret patterns; prompt injection; workspace tampering; context limits; time/output
limits; provider retries; GitHub rate limits/redirects; stale-base and publication boundaries.

PostgreSQL tests require disposable TEST_POSTGRES_URL and otherwise skip explicitly.
Windows symlink tests may skip if OS privileges prevent link creation.
Skips are not counted as passes.

Frontend tests cover truthful empty states, scenario selection, unavailable engine errors,
replay labeling and actual output rendering. Typecheck/build and browser inspection are
separate verification layers.

CI installs locked dependencies, runs checks/coverage/builds, audits dependencies and tests
PostgreSQL. Workflow configuration alone is not a passing CI result.
Optional live GitHub and paid-model tests remain separate from deterministic CI.

Measured local statement scope: 648 statements, 619 covered, 29 missing (95.52%).
Coverage.py also excludes the Provider protocol method stub and adjacent blank lines
(four lines) through its default ellipsis rule. There are no custom test-driven coverage exclusions. Linux CI covers one
additional symlink-path statement (620/648, 95.68%). Local JUnit paths are redacted to
[repository]; counts, outcomes and timings are unchanged.

Vitest 5.0.5 requires Node 22.12+ (official migration guide:
https://vitest.dev/guide/migration/). Full npm audit includes development dependencies.

## V2 checks

Owner/GitHub App/provider tests add real RSA signing, mock HTTP boundaries, session expiry,
CSRF, path policy, conservative budgets, concurrent reservation, idempotency, approval binding,
cancellation races and restart recovery. These do not count as live provider or App access.
Coverage includes all `repopilot` modules except the existing CLI exclusion; no V2 service
module is excluded. CLI behavior is exercised by demonstrations rather than included in coverage.

The recovered V2 full local suite passed 110 tests with two environment skips and 95.61%
statement coverage (`evidence/v2-local-tests.xml`, `v2-local-coverage.json`). These files precede
the additional cancellation/PostgreSQL tests; current CI is authoritative for the published head.
Eight frontend component tests passed. TypeScript found an unknown-valued conditional in the
new owner view; it was corrected to an explicit boolean, with a new build required.

CI browser tests use Chromium against the production static export and the production owner
frontend plus an actual loopback FastAPI test server. No credentials or paid APIs are used.
They check desktop/mobile evidence interactions, lack of public API calls, login/logout,
unauthorized access and closed execution gates. Screenshots and traces are CI artifacts.
Browser assertions do not constitute comprehensive accessibility or visual design review.
Configuration follows [Playwright's CI documentation](https://playwright.dev/docs/ci-intro).

```sh
cd frontend
npm run build
PUBLIC_BASE_PATH=/repopilot-ai npm run build:public
npx playwright install --with-deps chromium
npm run test:browser
```

Use a Python environment with the locked project dependencies for the browser test server.
Both test services bind to loopback and use temporary data. CI also runs owner migrations and
persistence/recovery against PostgreSQL 17; local PostgreSQL tests skip when unconfigured.
