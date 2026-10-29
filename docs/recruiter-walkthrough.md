# Recruiter walkthrough

Position this as an early-career backend / AI automation engineering reference focused on
controlled repository modification and verification evidence.

1. Open [the public demo](https://naraya07pedro-spec.github.io/repopilot-ai/); no setup or login.
2. Select **Bug fix**, then **Plan** and **Code diff** to inspect the scoped one-line change.
3. In **Tests**, compare the failing baseline with the actual passing candidate output.
4. Open the real **draft PR #2** and check its commit and Issue #1 reference.
5. Select **Rejected regression**: failed validation is preserved and no PR was prepared.
6. For independent reproduction, follow [local setup](../README.md#local-setup--no-paid-services)
   and [demo commands](demo.md). Only this local fixture path starts new execution; the public
   website displays recordings and never calls a model or changes a repository.

Evaluate whether policy is enforced independently of model text, approval can be tampered
with, failed/cancelled/interrupted states remain truthful, uncertain writes are retried
unsafely, and another engineer can reproduce the result.

Skills evidenced: Python/FastAPI, runtime schemas, Git, SQL concurrency/idempotency,
bounded subprocesses, HTTP contracts, failure handling, security policy, Next.js/TypeScript
and reproducible checks. Do not turn fixture results into claims about customers,
production reliability, business impact, seniority or employment duration.

## Private V2 work is separate

Start at [the public demonstration](https://naraya07pedro-spec.github.io/repopilot-ai/).
It requires no credentials and was verified over HTTPS with desktop/mobile Chromium flows.
PR #4 is merged. The separate private control plane remains partial; live model and isolated
private execution are not claimed. See the current release gates before evaluating readiness.

Use the static viewer to compare the failed baseline, exact one-line diff, passing checks
and actual draft PR #2. Every run is labeled a recording. PR #4 adds the separate owner
control plane with security and failure-path tests; it does not establish production
readiness or live model quality. Read private-workspace.md for the remaining execution gate.
