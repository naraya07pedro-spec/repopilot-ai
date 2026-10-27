# V2 release gates

Recovered V1 at 427a2b953a796d45407014ee525f8f1e3d3cb787. PR #3 was merged normally
as a6ef16f1e6fa8e0c5cd285fc85bd34a0d2426ade after clean review/CI state. PR #2 remains draft.

- [x] Preserve fixture engine, evidence, CI, and existing UI.
- [ ] Public static evidence viewer built and tested.
- [ ] Public HTTPS deployment independently verified.
- [ ] Owner session authentication, revocation, CSRF and throttling tested.
- [ ] GitHub App repository scoping and token lifecycle contract-tested.
- [ ] Live GitHub App installation validated (credentials absent).
- [ ] Real-model planning, usage and spending controls contract-tested.
- [ ] Authorized paid-model task validated (key/budget absent).
- [ ] Private repository execution on reviewed isolated infrastructure (unavailable).
- [ ] Durable private run state, approval, cancellation/recovery verified.
- [ ] Private production deployment and PostgreSQL migration verified.
- [ ] Browser end-to-end / visual QA verified (browser runtime currently times out).

V2 remains PARTIAL until every required release gate has independent evidence.
No arbitrary repository code will run on this host. No new repository will be created.
