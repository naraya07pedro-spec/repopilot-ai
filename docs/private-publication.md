# Private publication and worker integration

Production dispatch and publication stay closed. The new components are executable integration
code with deterministic tests, not evidence of a live worker or a newly published coding-agent PR.

## Repository inspection

REPOPILOT_SOURCE_ROOTS is an operator-only JSON mapping from an allowed repository to a bounded
relative directory, for example {"naraya07pedro-spec/repopilot-ai":"fixtures/bug"}. Invalid,
hidden, absolute and traversing scopes are rejected. Inspection reads only selected source
files at a pinned commit, with the original count/byte limits. Run identity binds the configured
scope; a changed scope cannot silently redirect a queued task. The approved snapshot includes
the prefix, baseline commit and Git tree used to map a future patch to its original location.

## Worker transport and staging

worker_dispatch.py stages validated text in a fresh temporary directory; it never imports or
executes candidate files. Snapshot checks detect tampering and cleanup is limited to the owned
temporary directory. WorkerTransport accepts only an explicit literal loopback HTTP endpoint.
The transport rejects clients unless trust_env=False, so environment proxies cannot redirect job data.
Production has no configured transport or runtime enable switch. A future controller must keep
its HMAC key and transport outside the tested sandbox.

POST /v1/execute sends the existing job envelope and expects a signed execution receipt.
POST /v1/cancel sends a domain-separated cancellation envelope binding run, nonce, job digest and
lease expiry. Responses are bounded to 256 KB, redirects are denied, and no request is retried.
A lost or invalid execution response marks durable state interrupted. Cancellation stays requested
until a valid acknowledgement arrives. The loopback HTTP test uses an actual temporary server,
with synthetic signed receipts and no code execution. It is not an isolated-worker acceptance test.

## Publication and reconciliation

PrivatePublisher derives a separately approved artifact from the exact candidate, baseline and
successful receipt. It rechecks repository scope, explicit publication digest, approval expiry,
remote baseline and App write permissions before the first repository mutation. Atomic state
claims prevent concurrent writers. A deterministic task branch and publication marker tie the
remote PR to the stored artifact. Each confirmed tree/commit identity is saved before continuing.

No write is retried. Unknown outcomes become publication_unknown, including restart during a
write. Reconciliation reads branch, commit parents/tree and the unique marked PR, checking exact
commit/repository/base identities. It performs no repository writes and cannot recreate a PR.
Missing or conflicting results stay unresolved. If acknowledgement was lost before a confirmed
commit, an operator must inspect orphaned objects and review a new attempt; no automatic resume.

Owner routes expose the artifact preview, gated publication and read-only reconciliation using
the existing authentication and Origin checks. The UI renders actual saved receipt command
outputs and PR identities. Publication remains disabled by the same closed runtime gate even
when an artifact exists. There is no automatic merge or widening to unapproved repositories.

Synthetic HTTP tests cover normal publication, lost acknowledgements at every write, stale base,
revoked scope, concurrent calls, external branch/PR conflicts, duplicate PRs and restart recovery.
They validate API/state behavior, not live GitHub App authentication or sandbox correctness.
