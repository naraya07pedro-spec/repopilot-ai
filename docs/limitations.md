# Limitations

- Only audited Python fixture bytes and approved edits execute. Arbitrary repositories and
  arbitrary model-generated code remain disabled.
- Default plans/edits are deterministic. Live model quality, cost and token counts are unverified.
- Inspection supports the Python/pytest fixture profile, not general framework detection.
- One service process; no distributed scheduling, leases or automatic interrupted-run resume.
- PostgreSQL and Docker passed in Linux CI; both are unavailable locally.
- Live GitHub ingestion and connector-assisted publication were verified. The application token
  publisher and paid model adapter remain contract-tested only.
- Unknown publication outcomes need manual reconciliation; no exactly-once remote-write claim.
- Secret scanning is incomplete. Catalog authors, host operator and filesystem are trusted.
- The console is local; no public writable deployment is supported.
- Browser visual QA is blocked by webview attachment timeouts; no screenshots were fabricated.
  Component tests and production HTTP workflow checks passed. Device/accessibility QA remains open.
- Connected GitHub integration lacks branch-protection administration access.
- Portfolio integration waits for project acceptance; the existing portfolio remains untouched.
