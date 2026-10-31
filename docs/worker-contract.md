# Worker job and execution-receipt contract

Status: implemented and tested as a protocol/state machine. The [Linux runtime](linux-worker.md),
HTTP transport and publication integration are implemented but **not activated or live-validated**. The private execute route returns 409. Nothing in this
module launches a subprocess, provisions a machine, mounts a socket or writes candidate files.
A signed receipt authenticates a message; it does not independently prove isolation or execution.

## Control-plane lifecycle

The existing private run table stores the job, receipt and events. No queue or schema change
is required. The ledger accepts only an approved plan whose repository is still allowlisted,
configuration matches, digest matches the exact plan/snapshot/budget, and approval has not expired.
The owner inspects the derived unified diff before approval. The ledger combines the inspected
source with approved full-file edits in memory. Only bounded Python
source is eligible for this first verification profile; TypeScript planning remains inspection only.

```mermaid
stateDiagram-v2
    approved --> worker_queued: persist authenticated job
    worker_queued --> executing: single atomic claim
    executing --> verification_passed: all three checks pass
    executing --> verification_failed: failed or incomplete checks
    worker_queued --> cancel_requested
    executing --> cancel_requested
    cancel_requested --> cancelled: authenticated acknowledgement
    worker_queued --> interrupted: restart
    executing --> interrupted: restart
    cancel_requested --> interrupted: restart
```

A verified receipt alone cannot publish. The separate [publisher](private-publication.md) requires
a matching candidate, exact publication approval and remote reconciliation. Its production gate
remains closed until runtime isolation is independently verified. Profile python-checks-v2 uses
pytest on the candidate root so both root-level and tests/ layouts work. Legacy v1 jobs are
rejected; generate and approve a new run rather than silently changing existing commands.

## Job and receipt boundaries

- HMAC-SHA256 uses distinct job/receipt domains, constant-time comparison and a minimum 32-byte
  controller key. The key is never included in a message, source file or stored run payload.
- A unique job nonce binds run ID, baseline commit, approval digest, source and resource policy.
  Repeated preparation returns the existing job. Repeated claims cannot run it twice.
- Jobs expire after at most five minutes and never outlive approval. Claims recheck configuration
  and repository allowlisting. Unknown fields, unsafe paths, case aliases, Windows device names,
  credential patterns, overlarge source and unsupported profiles are rejected.
- Resource requirements: non-root UID 65532, denied network, at most one CPU, 512 MiB memory,
  64 MiB writable disk, 32 processes and 60 seconds total checks. These are **declared requirements**,
  not currently enforced operating-system isolation. No host executor consumes these jobs.
- Fixed pytest/Ruff command arrays are selected by the protocol; no model-provided shell command,
  environment, package installation or filesystem mount is accepted. The runtime must separately
  suppress plugin/config discovery and supply trusted tools outside candidate-controlled paths.
- Receipts must match the exact job digest and nonce. Successful verification requires all three
  unique command outcomes, zero exit codes and no timeout/cancellation. Outputs and durations are
  bounded; secret-pattern outputs are rejected. Test counts are not inferred from prose.
- Receipt replay after a lost acknowledgement is idempotent. A conflicting/stale receipt is rejected.
  Cancellation remains requested until acknowledgement; requesting cancellation does not claim a
  process was stopped. Restart marks all active jobs interrupted, including jobs beyond the first
  history page. Recovery never automatically repeats uncertain execution or publication.

## Tests and remaining runtime work

`python -m pytest tests/test_worker_contract.py -q` exercises signed-message tampering, forged
receipts, duplicate/concurrent claims, revoked repositories, expired approval/leases, changed
configuration, failed checks, receipt replay, cancellation races and restart recovery.
Receipts in these tests are explicitly synthetic protocol fixtures. Provider/browser contract
responses are also synthetic; their successful checks are not live model or sandbox evidence.

Before any production dispatcher is enabled, supply a separately reviewed disposable VM/microVM
worker with a secret-free guest and authenticated external controller. Independently demonstrate
network denial, filesystem containment, non-root identity, CPU/memory/disk/process enforcement,
process-tree cancellation, teardown on crash and adversarial escape/resource tests. The controller
must keep its authentication key outside tested code, validate receipt identity and reconcile
unknown outcomes. Docker Compose smoke checks of the application do not establish this boundary.

No suitable local runtime, Docker or installed WSL was available during this implementation.
No paid resources were created. The existing exact-byte fixture runner remains the only executable
repository path. General model-generated code stays disabled until this release gate is satisfied.
