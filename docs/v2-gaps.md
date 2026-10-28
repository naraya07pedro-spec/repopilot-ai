# V2 release gates

Recovered V1 at 427a2b953a796d45407014ee525f8f1e3d3cb787. PR #3 was merged normally
as a6ef16f1e6fa8e0c5cd285fc85bd34a0d2426ade after clean review/CI state. PR #2 remains draft.

- [x] Preserve fixture engine, evidence, CI, and existing UI.
- [x] Public static evidence viewer built and tested.
- [x] Public HTTPS deployment independently verified (main 1e79482, deployment 40639065386).
- [x] Owner session authentication, revocation, CSRF and throttling tested.
- [x] GitHub App repository scoping and token lifecycle contract-tested.
- [ ] Live GitHub App installation validated (credentials absent).
- [x] Real-model planning, usage and spending controls contract-tested.
- [ ] Authorized paid-model task validated (key/budget absent).
- [ ] Private repository execution on reviewed isolated infrastructure (unavailable).
- [x] Durable private run state, approval, cancellation/recovery verified.
- [ ] Private production deployment and PostgreSQL migration verified.
- [x] CI browser E2E: public desktop/mobile and owner authentication; genuine screenshots inspected.
- [x] Live hosted URL browser validation at desktop/mobile widths (2 Chromium tests).
- [ ] Comprehensive accessibility/device review.

V2 remains PARTIAL until every required release gate has independent evidence.
No arbitrary repository code will run on this host. No new repository will be created.

Checked private-state items describe local SQLite/HTTP contract tests; production and live integrations remain separate unchecked gates.
