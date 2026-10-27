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
python -m repopilot.cli live --scenario bug --issue ISSUE_NUMBER --ref feat/verified-issue-to-pr --output evidence/live-bug.json
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
