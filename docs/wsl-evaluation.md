# WSL2 prerequisite evaluation — 31 October 2026

Ubuntu is operational. **This is a prerequisite audit, not sandbox acceptance.** No model,
container engine, image, driver or package was installed, and no repository/model code ran.
The public portfolio release and the preserved PR #8 sandbox failures are unchanged.

## Actual results

| Check | Observed result |
| --- | --- |
| Distribution/kernel | Ubuntu 24.04.5; 6.18.54.1-microsoft-standard-WSL2; WSL 3.0.3.0 |
| Linux identity | Non-root UID 1000 (`repopilot`); systemd and its user manager running |
| WSL RAM/swap | 1,912,164,352 bytes RAM (1.78 GiB), about 1.40 GiB available; 1 GiB swap unused |
| Processors | Four logical processors |
| Windows physical RAM | Still one 4 GB module; about 502 MiB available at the initial sample |
| Physical disk | C: about 29.8 GiB free; the virtual ext4 filesystem's roughly 1 TB capacity is not physical free space |
| Rootless namespaces | Fixed `unshare --user --map-root-user --net /bin/true` exited 0 |
| Cgroups | v2, CPU/memory/PIDs controllers; user service `Delegate=yes`; global root not writable |
| Bounded child service | UID 1000; cpu.max `25000 100000`, memory.max `67108864`, memory.swap.max `0`, pids.max `16`, NoNewPrivs `1` |
| Cleanup | Transient service inactive after stop/collection; no packages or application settings changed |
| KVM | Device exists; current user cannot open it; no VM runtime was installed or tested |
| Host integration | Windows drives mounted and Windows executable interop enabled — unsuitable for adversarial probes |
| Missing Linux tools | Ollama, Podman, Docker, runsc, newuidmap and newgidmap |

The transient child only reads its kernel settings. It does not stress CPU/memory/PIDs or prove
resource enforcement under attack, filesystem confinement, network denial, disk limits, sandbox
escape resistance, cancellation of hostile process trees or crash recovery. A successful
namespace syscall does not establish any of those properties. No six-probe sandbox pass is claimed.

## Reproduce the bounded audit

From the Windows repository root, using the already installed Linux Python:

```powershell
pwsh -NoProfile -File ./scripts/audit-local-windows.ps1
Get-Content -Raw scripts/audit_wsl.py | wsl --distribution Ubuntu-24.04 --user repopilot --cd /home/repopilot --exec python3 - --probes
```

Omit `--probes` for read-only collection. The optional probes start fixed, bounded, trusted
processes and a transient systemd user service; its journal entries may remain. They never run
task commands, access credentials, install dependencies, connect to the network or authorize
owner execution. Read each result/exit code: JSON output alone is not a passing sandbox verdict.
[Measured record](../evidence/wsl-local-readiness-2026-10-31.json).

This laptop's existing PowerShell 7 ran the Windows audit. Windows PowerShell 5 blocked its
script under the existing execution policy; that policy was not changed or bypassed.

## Local app is testable now; inference is not yet measured

The existing Windows Python/Node installations and production frontend build ran successfully
with a real FastAPI backend and fresh temporary SQLite database. Chromium verified actual owner
login/logout, authentication/origin rejection, two local profiles, disabled repository/planning
controls without App authorization, a truthful unavailable-Ollama error, and mobile login layout.
The stored owner session remained valid after restarting the actual API with the same database.
No GitHub/provider mocks or paid calls were used in this smoke test. This exercised no model and
no candidate code; the worker remained disabled. The temporary services and data were removed.

Available Windows RAM fell from about 580 MiB to 446 MiB with API/Next running (before browser
startup); it was about 713 MiB after cleanup. These are snapshots, not peak measurements or total
application footprints. Guest and host available memory overlap; do not add them. The test shows
the dashboard can operate, not that concurrent inference and isolated tests fit reliably.

No local model runtime is installed. The smallest prepared coding-family smoke candidate remains
Qwen2.5-Coder 0.5B Q4 (398 MB weights); 1.5B Q4 (986 MB) needs a separate feasibility/quality trial.
Neither is live-tested or claimed practical. Ollama's native Windows installation itself requires
at least 4 GB disk, plus model storage. Current physical disk can accommodate those nominal
artifacts, but RAM headroom remains insufficient to justify installation/generation during this
session. No larger model or heavy container infrastructure was downloaded.

Next inference evaluation is sequential: with genuinely available memory, install/reuse only an
approved local runtime, disable cloud access, load only the 0.5B candidate with bounded context,
measure latency/peak RAM and schema validity, then unload it before worker evaluation. Existing
profiles already bound context/output and `keep_alive=0`. Do not increase limits or silently
switch models/endpoints if the candidate fails. Generation success still would not authorize code
execution. [Memory/model details](local-feasibility.md).

## Remaining engineering gates

1. Evaluate a reviewed, compatible runtime only after capacity permits. The released rootless
   gVisor/systemd and cgroupfs configurations in PR #8 failed before guest execution. WSL boot
   and user cgroup support do not resolve the upstream runtime failure. Do not repeat it unchanged.
2. Before any adversarial test, isolate the worker environment from Windows drives, interop,
   credentials, model endpoints and the control-plane filesystem. A dedicated disposable distro
   is preferable. For such a distro, merge `[automount] enabled=false, mountFsTab=false` and
   `[interop] enabled=false, appendWindowsPath=false` into its `/etc/wsl.conf`, restart that distro
   only after saving work, and verify the actual absence of Windows mounts/interop. Do not change
   this owner's active Ubuntu configuration silently. This hardening still is not a sandbox.
3. Preserve non-root guest execution, all CPU/memory/PID/disk/time limits and network/filesystem
   restrictions. Run the six existing real probes, then teardown/cancellation/recovery acceptance.
   No Docker socket, privileged execution or host-command fallback is permitted.
4. Only after that evidence passes: review dispatcher binding, authenticate worker transport,
   generate an actual local-model candidate, approve its exact scope/model/budget, run isolated
   tests and separately approve/reconcile a draft PR. None of this acceptance has run.

## Owner-only actions

**No additional Windows administrator action is presently required for this audit or dashboard.**
WSL installation is complete; do not reinstall it or enable Docker Desktop. There is no reason to
grant KVM access or install another runtime before choosing a proven, capacity-compatible path.

The remaining GitHub authorization is the read-only, selected-repository App installation/key
described in [owner activation](owner-activation.md#github-app-configure-read-only-planning-first).
Keep its key outside Git/chat. Write permissions remain deferred until sandbox acceptance and
explicit draft-PR approval. No model account, API key, paid service or rented server is required.

Primary documentation: [WSL settings and restart semantics](https://learn.microsoft.com/en-us/windows/wsl/wsl-config),
[Ollama Windows disk requirements](https://docs.ollama.com/windows),
[local concurrency/context controls](https://docs.ollama.com/faq),
[0.5B model artifact](https://ollama.com/library/qwen2.5-coder:0.5b).
