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
- Three actual CI Chromium tests passed, covering public desktop/mobile interactions and owner
  authentication. Genuine screenshots were inspected. Native desktop control later stopped
  because the browser URL could not be established safely. Full device/accessibility QA remains open.
- Connected GitHub integration lacks branch-protection administration access.
- Portfolio integration waits for project acceptance; the existing portfolio remains untouched.

V2 private planning supports only small Python/TypeScript repositories, with strict context
limits. Live GitHub App authentication and real-model calls await credentials and approved
budget. Private modification, isolated verification and PR publication are not implemented.
Private deployment, production PostgreSQL recovery and hostile-code sandbox validation remain
blocked. Static public export is available; hosting status is tracked in deployment.md.
