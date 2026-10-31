# Private owner workspace (V3, partial)

The owner UI at `/owner` supports login, repository validation, issue planning, plan
approval/rejection, cancellation and durable history. It does **not** execute arbitrary
code or publish private PRs: those routes remain closed until a validated isolated worker
has passed host validation and is wired into owner dispatch. No live model or GitHub App installation call has been verified.
Contract tests use mock HTTP responses, real signing and real database transactions.

## Configure locally

Use the README Python/Node setup. Generate a password hash with
`python scripts/hash_owner_password.py` (the password is read without echo). Supply the hash
as `REPOPILOT_OWNER_PASSWORD_HASH` using your shell's literal-string quoting. Do not commit it.
Set `REPOPILOT_MODE=owner`, `REPOPILOT_ORIGIN=http://localhost:3000`, and
`REPOPILOT_COOKIE_SECURE=false` for loopback development only. Open `/owner`.
Default local mode retains the audited fixture demo; owner mode blocks those write routes.
The static public build contains neither the owner page nor its API proxy.

For HTTPS hosting set `REPOPILOT_ENV=production`, `REPOPILOT_MODE=owner`,
`REPOPILOT_ORIGIN=https://your-owner-host`, and `REPOPILOT_COOKIE_SECURE=true`.
Set the same `REPOPILOT_ORIGIN` on both Next.js and FastAPI. The proxy compares this trusted
external origin rather than Next.js's internally normalized URL. Use one application process,
PostgreSQL and a private backend network.

Production additionally requires `REPOPILOT_DATABASE_SCHEMA` to name a dedicated private
schema and `DATABASE_URL` to use `postgresql+psycopg` with `sslmode=verify-full`. Create the
schema under a dedicated application role first. Startup rejects public/shared schemas and
SQLite; it never falls back to the public schema. See [exact hosting setup](hosting-setup.md)
and `deploy/owner.env.example`. Supabase connections require the same safeguards in every mode.

## GitHub App

Create an App installed only on explicitly approved repositories. Planning requires
Metadata read, Contents read and Issues read. No webhook is used. Set server-side
`GITHUB_APP_ID`, `GITHUB_INSTALLATION_ID`, `GITHUB_APP_PRIVATE_KEY_FILE` (a mounted PEM secret),
and `REPOPILOT_REPOSITORIES` (comma-separated `owner/repository` names, no whitespace).
No private key or token is accepted in the UI. Installation identity and permissions are
checked; short-lived tokens are scoped to one selected repository and refreshed before expiry.
Only allowlisted repositories are queried. Revoked tokens fail closed; reauthentication is
required after revocation rather than silently retrying writes.

The inspection profile accepts up to eight Python/TypeScript source files, 12 KB per file,
24 KB aggregate, and a maximum 1,000-entry tree. Larger repositories are rejected explicitly.
Set REPOPILOT_SOURCE_ROOTS to {"naraya07pedro-spec/repopilot-ai":"fixtures/bug"} for
this repository. Whole-repository inspection exceeds this profile; the server-selected scope
keeps the acceptance task within the existing authorization. Inspection reads a pinned commit and never clones or runs code.

## Real provider and budgets

The owner model selector now uses the server-side registry described in [providers.md](providers.md).
It supports OpenAI, Anthropic, Gemini, Ollama and explicit local compatible profiles. All are
contract-tested; none is presented as live-validated. Paid requests require server opt-in and
per-run consent. Model/budget selection is included in the approval digest and expires in one hour.
The legacy single-model configuration below is retained for API clients, with the additional
required REPOPILOT_ALLOW_PAID_MODELS=true gate; use profiles for the current owner UI.

Set server-only `OPENAI_API_KEY` and `REPOPILOT_MODEL` to a model supporting Chat Completions
structured JSON-schema output. Set `REPOPILOT_DAILY_USD`, `REPOPILOT_RUN_USD`,
`REPOPILOT_INPUT_USD_PER_MILLION` and `REPOPILOT_OUTPUT_USD_PER_MILLION` only after approving
spend and checking the provider's current prices. All budget defaults are zero, disabling calls.
Rates must be conservative upper bounds for that model. Costs are estimates, not invoices.

The adapter uses a fixed HTTPS endpoint, bounded input/output, a 30-second HTTP timeout,
strict Pydantic validation, and at most two attempts for explicit 429/502/503 responses.
Daily reservations use atomic database updates. A run must fit two conservative reservations.
Unknown transport outcomes are not retried and reservations are never refunded automatically.
Cancellation cannot undo a provider request already sent; it prevents subsequent state advancement.
Reported usage comes from provider fields when present and valid. No paid request ran during delivery.

## Approval, persistence and recovery

The owner sees a bounded unified diff derived from the pinned snapshot and proposed full-file
edits before approval. New-file and missing-newline markers are preserved. No-op plans and
overlarge previews fail closed. This preview only manipulates text; it never writes or runs code.
The approval digest binds the inspected commit, source snapshot and exact proposed edits.
Approval records intent but never starts arbitrary execution. `/execute` returns 409 with
`isolated_worker_unavailable`. No private PR write is attempted. V1 fixture PR publication
remains a distinct operator workflow described in `demo.md`.

Sessions expire in one hour; only token digests are stored. Login is limited to five attempts
per minute per process. Mutation routes require the configured Origin. Logout revokes the
session. Run creation uses a unique idempotency key plus request fingerprint. On restart,
queued/planning and worker-protocol active states become interrupted; uncertain calls are never
automatically replayed. The [worker ledger](worker-contract.md) is tested but not dispatched.
There is no distributed scheduling or automatic resume. Publication restart state is
publication_unknown; reconciliation reads confirmed remote identities without repeating writes.
The separate worker journal also prevents replay after a crash. Use a new request only after review.
Private snapshots and plans reside in the database: apply storage encryption, access control,
backups and retention at the hosting layer. They are never copied into public recordings.

See [Windows local startup](local-owner-windows.md) and [scoped inspection/publication](private-publication.md). REPOPILOT_SOURCE_ROOTS can restrict this repository to fixtures/bug, so it no longer needs whole-repository inspection for that scenario. The configured mapping cannot be changed by browser requests.
