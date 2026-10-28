# Private owner workspace (V2, partial)

The owner UI at `/owner` supports login, repository validation, issue planning, plan
approval/rejection, cancellation and durable history. It does **not** execute arbitrary
code or publish private PRs: those routes remain closed until a validated isolated worker
is implemented and available. No live model or GitHub App installation call has been verified.
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
The current project itself exceeds this small-repository profile. Use an explicitly approved
small test repository for a future live planning check; approval to access an unrelated
repository must be obtained separately. Inspection reads a pinned commit and never clones or runs code.

## Real provider and budgets

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

The approval digest binds the inspected commit, source snapshot and exact proposed edits.
Approval records intent but never starts arbitrary execution. `/execute` returns 409 with
`isolated_worker_unavailable`. No private PR write is attempted. V1 fixture PR publication
remains a distinct operator workflow described in `demo.md`.

Sessions expire in one hour; only token digests are stored. Login is limited to five attempts
per minute per process. Mutation routes require the configured Origin. Logout revokes the
session. Run creation uses a unique idempotency key plus request fingerprint. On restart,
queued/planning runs become interrupted; uncertain calls are never automatically replayed.
There is no distributed worker lease or automatic resume. Use a new request only after review.
Private snapshots and plans reside in the database: apply storage encryption, access control,
backups and retention at the hosting layer. They are never copied into public recordings.
