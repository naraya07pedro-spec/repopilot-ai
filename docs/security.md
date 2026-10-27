# Security and trust boundaries

Inputs include issue text, repository files, provider output and command output.
Attackers may request credentials, traversal, malicious commands, workflow edits,
unauthorized PRs, or misleading success claims.

**Host execution accepts only reviewed fixture and candidate bytes.** The runner independently
checks catalog membership, then checks all files before and after execution. An allowed
filename alone is insufficient. The provider cannot authorize executable content.

| Threat | Control | Limit |
| --- | --- | --- |
| Prompt injection | Untrusted data fields; provider cannot choose commands or authority | Prompt wording alone is not a security boundary |
| Traversal / Windows aliases | Relative paths, resolved containment, symlink rejection, exact file policy | Host administrators are trusted |
| Credential exposure | Clean child environment, no inherited API keys, pattern redaction | Scans are not exhaustive |
| SSRF | Fixed GitHub/OpenAI origins, validated repository names, redirects disabled | Host DNS and operator clients are trusted |
| Workflow/dependency changes | Exact app/test paths and content enforced | General dependency edits unsupported |
| Arbitrary code | No clone-and-run endpoint; runner enforces byte gate | Not a general sandbox |
| Resource exhaustion | Two workers, context/output budgets, Git and test timeouts | No per-child memory sandbox on Windows |
| Concurrent replay | Unique key, fingerprint, atomic claims | One process; no distributed leases |
| Approval tampering | Plan/issue/baseline digest and state checks | Local demo approval is public for fixed fixtures |
| Unauthorized publishing | Operator action, repo/file scope, digest, remote-base check | Uncertain writes need manual reconciliation |
| False success | Actual exit codes and policy errors govern status | Passing fixtures do not prove general correctness |

Git hooks and system/global Git config are excluded. Tests use explicit config and workspace
root; plugin autoload and conftest discovery are disabled. Argument arrays run without a shell.
No dependencies are installed in task workspaces.

## Credentials

Prefer a GitHub App limited to the approved test repository: metadata/issue read, contents
read/write, pull requests read/write. A scoped fine-grained token is a fallback, injected
through environment only. Setup issue creation additionally needs issues write.
Tokens never belong in URLs, browser code, logs or artifact descriptions.

## Deployment

Compose drops capabilities, enables no-new-privileges, runs a non-root backend and bounds
memory, CPU and processes. Docker alone is not a complete security boundary.

Do not remove the byte gate to enable arbitrary execution. That requires a reviewed disposable
VM/microVM executor with denied network, secret-free runtime, filesystem/resource isolation,
teardown and escape testing. Until then, general execution is disabled.

Never publicly expose the writable demo. A hosted recruiter demo should serve recorded evidence
read-only with no credentials. Branch-protection integration limits are recorded in evidence.
