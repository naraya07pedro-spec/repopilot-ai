# Recruiter walkthrough

Position this as an early-career backend / AI automation engineering reference focused on
controlled repository modification and verification evidence.

1. Read the execution boundary.
2. Run the bug fixture in the console.
3. Observe baseline failure; inspect and approve the plan.
4. Compare the minimal diff with actual passing output.
5. Inspect commit, PR artifact and linked GitHub evidence.
6. Run the failure fixture: it must stop without preparing a PR.

Evaluate whether policy is enforced independently of model text, approval can be tampered
with, failed/cancelled/interrupted states remain truthful, uncertain writes are retried
unsafely, and another engineer can reproduce the result.

Skills evidenced: Python/FastAPI, runtime schemas, Git, SQL concurrency/idempotency,
bounded subprocesses, HTTP contracts, failure handling, security policy, Next.js/TypeScript
and reproducible checks. Do not turn fixture results into claims about customers,
production reliability, business impact, seniority or employment duration.

## V2 review

Use the static viewer to compare the failed baseline, exact one-line diff, passing checks
and actual draft PR #2. Every run is labeled a recording. PR #4 adds the separate owner
control plane with security and failure-path tests; it does not establish production
readiness or live model quality. Read private-workspace.md for the remaining execution gate.
