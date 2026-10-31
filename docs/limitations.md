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
- Chromium tests cover public desktop/mobile interactions, both static URL layouts, owner
  authentication and disabled private execution. Local and CI browser results are recorded in
  evidence.md. Genuine screenshots were inspected. Full device/accessibility QA remains open.
- Connected GitHub integration lacks branch-protection administration access.
- Portfolio integration waits for project acceptance; the existing portfolio remains untouched.

V2 private planning supports only small Python/TypeScript repositories, with strict context
limits. Live GitHub App authentication and real-model calls await credentials and approved
budget. Candidate text staging, bounded worker transport and publication reconciliation are
implemented and contract-tested. Isolated verification and private publication remain disabled
as a connected runtime. Worker receipts in tests are synthetic, not execution evidence.
The experimental sandbox and all six failed live probes remain preserved in
[PR #8](https://github.com/naraya07pedro-spec/repopilot-ai/pull/8). They are not part of this
application release; passing its CI does not establish worker security or real-agent completion.
Private deployment, production PostgreSQL recovery and hostile-code sandbox validation remain
deferred. The public GitHub Pages demo is deployed; Netlify publication is pending by owner
decision. Additional cloud resources, paid models and private hosting are outside the current
zero-additional-cost portfolio release. Existing Supabase bootstrap validation used a rollback-only
transaction; no persisted application installation or driver connection is claimed.
