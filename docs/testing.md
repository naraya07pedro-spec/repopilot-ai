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
