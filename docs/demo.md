# Demonstrations

All scenarios are self-contained seeded fixtures, never customer repositories.

| Scenario | Baseline | Candidate | Expected |
| --- | --- | --- | --- |
| bug | Fractional mean assertions fail | Replace floor division | verified |
| feature | Existing normalization passes | Add stable unique tags and tests | verified |
| failure | Mean tests fail | Incorrect rounding still fails | failed; no PR |

Run python -m repopilot.cli demo --scenario bug (or feature / failure).
Failure must exit 1. CLI demo invocation authorizes only catalog edits; the UI pauses for
explicit plan approval. Every run creates real Git history and independent test evidence.

## Live GitHub

Publish fixture baselines on the approved project branch. Create an issue with the marker
repopilot-scenario: bug and the exact acceptance criteria in the bug catalog.

```sh
python -m repopilot.cli live --scenario bug --issue 1 --ref feat/verified-issue-to-pr --output evidence/live-bug.json
```

The engine reads the actual issue and commit-pinned fixture bytes, validates the binding,
then executes. Successful runs also write live-bug.pr.json. Review it and its digest.
With a repository-scoped token supplied outside source control:

```sh
python -m repopilot.cli publish --artifact evidence/live-bug.pr.json --approve-digest REVIEWED_DIGEST
```

Never auto-merge. On an uncertain write, inspect refs/PRs before retrying manually.
The authoring session may use the connected GitHub integration to publish the exact artifact
without exporting credentials. Evidence distinguishes this bridge from a live invocation
of the application's token publisher.

The console's replay is actual saved output, explicitly labeled; it never starts a new run.

## Saved live execution

Issue #1 and draft PR #2 are the actual published demonstration. See docs/evidence.md.
The PR remains unmerged so the review branch retains the defective baseline for reproduction.
The saved replay is frontend/public/replay.json, copied from evidence/live-bug.json.

## Production HTTP workflow

Start the API on 127.0.0.1:8000. In frontend run npm run build and npm start, then from
repository root run python scripts/smoke_http.py. It checks the real Next.js proxy, approval
boundary, idempotency, execution and history. It writes evidence/http-smoke.json.

On Windows, if an old generated build directory is locked, set REPOPILOT_BUILD_DIR to a new
.next-* directory for both build and start. This was tested with .next-verify. Do not commit
Next.js-generated alternate-directory changes to next-env.d.ts or tsconfig.json.
