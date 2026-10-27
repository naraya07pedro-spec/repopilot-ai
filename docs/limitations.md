# Limitations

- Only audited Python fixture bytes and approved edits execute. Arbitrary repositories and
  arbitrary model-generated code remain disabled.
- Default plans/edits are deterministic. Live model quality, cost and token counts are unverified.
- Inspection supports the Python/pytest fixture profile, not general framework detection.
- One service process; no distributed scheduling, leases or automatic interrupted-run resume.
- PostgreSQL, Docker and live integrations must be verified separately from SQLite/mocks.
- Unknown publication outcomes need manual reconciliation; no exactly-once remote-write claim.
- Secret scanning is incomplete. Catalog authors, host operator and filesystem are trusted.
- The console is local; no public writable deployment is supported.
- No exhaustive accessibility/browser/device certification is claimed.
- Connected GitHub integration lacks branch-protection administration access.
- Portfolio integration waits for project acceptance; the existing portfolio remains untouched.
