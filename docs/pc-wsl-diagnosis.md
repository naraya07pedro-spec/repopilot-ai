# PC WSL diagnosis: saved evidence and collector hang

As of 31 October 2026 (Asia/Jakarta), recovery has **not been validated**. The saved-evidence
review is offline; the subsequent bounded check reads Windows process/service/registry metadata.
Neither starts a WSL client or runs the retired Administrator collector.

## What the saved evidence establishes

- Six saved reports of genuine ELF cores identify init-systemd(Op... / PID 2 aborting with
  SIGABRT (6), code -6. Each contains the exact formatted Broken pipe exception at
  SocketChannel.h:183 (SendMessage). The latest recorded core is from 09:31 local time.
- Earlier actual /bin/true and /bin/echo attempts failed with Wsl/Service/E_UNEXPECTED,
  including explicit distro/root/Linux-cwd and terminal launches. Status/list success did
  not establish Linux execution.
- Earlier snapshots show Windows 11 Pro build 26200, WSL 2.7.11.0, enabled WSL/virtualization
  features and running WslService/vmcompute/hns/HvHost. OpenClawGateway is the only registered
  distro, WSL2, default UID 0, original C: VHDX about 4.64 GiB. These are recorded snapshots,
  not fresh evidence that the Linux broker is healthy.
- The local core exception and failure pattern match the same-version
  [upstream init/interop abort report #41592](https://github.com/microsoft/WSL/issues/41592).
  The initiating client and current live broker state remain unknown; no permanent fix is
  established from an issue being closed. No speculative systemd, networking or memory
  configuration change is justified.

The best-supported proximate failure is a repeatedly aborting WSL init/interop broker.
The Windows event selection does not identify an alternative cause or prove filesystem damage.
No raw core memory, credentials or process environment is published in this repository.

## The later Administrator run did start, but did not finish

The first UAC launch was canceled. The owner subsequently ran the collector and saved:

- admin-20261031-214737-a226bec8/local-event-messages.json at 21:47:38;
- pending-client.json at 21:48:04, naming WSL client PID 24704 past its 25-second deadline;
- no admin-result.json or completed VM/real-Linux validation output.

All four selected administrative event channels returned no matching entries for the
last-24-hours, levels-1-to-3 filter. The old collector caught that response as read_completed=false.
This means **no matching events in that selection**, not permission denied and not a clean bill
of health. Raw event bodies remain local; the offline report emits only classifications/counts.

The old collector's deadline branch then called WaitForExit() with no timeout. That unbounded
wait explains why Administrator PowerShell PID 28432 stayed stuck. This is a tooling defect,
separate from the WSL init abort. The failed invocation's arguments were not saved, so we cannot
prove whether the blocked WSL call was metadata enumeration or the debug shell.

The owner terminated PID 28432, and a process metadata check confirmed it was absent.
Its child WSL client PID 24704 was still present with parent PID 28432; its elevated command line
was not readable. The child was left untouched. That observation is time-bound and is not an
instruction to kill a PID later without rechecking its identity and obtaining approval.

## Retired collector: do not rerun

scripts/collect_wsl_admin.ps1 is now a fail-closed retirement notice. It performs no elevation,
process launch, wait or WSL operation. The previous implementation remains in Git history for
review, but must not be used for collection. No variant of the hanging live collector was run
during this follow-up.

Use the saved JSON analyzer from the existing Windows Python environment:

```powershell
.\.venv\Scripts\python.exe scripts/analyze_wsl_evidence.py D:\Projects\repopilot-local\wsl-diagnosis-2026-10-31
```

This tool has no subprocess, network, service or WSL calls. It reads bounded known JSON files,
supports the Windows report encodings, rejects paths escaping the selected evidence root,
distinguishes empty event selections from access errors, and flags missing or invalid completion
records. It never prints raw event-message bodies or authorizes recovery from an input field.

Saved D: metadata/exception reports were used as the real-core evidence. The small .dmp found
under the RepoPilot pytest temporary directory is a synthetic test fixture and is not counted
as a real crash. The bounded D: inventory did not find another raw crash export; this is not an
exhaustive search of every unrelated backup/project directory.

The existing scripts/inspect_wsl_crash_notes.py can inspect an explicitly selected raw core
directory offline when needed. Its default mode reads bounded ELF notes only. Its opt-in
--known-exception scan reads at most 1 MiB per file and emits only a strict public
error/source-path signature, never adjacent process memory.

## Safest targeted recovery proposal

The subsequent Windows-only snapshot completed in 9.641 seconds, inside its 15-second deadline,
with exit zero and no stderr. It reads no raw command lines into reports. WslService PID 4660,
vmcompute PID 1288, hns and HvHost report Running / exit code zero / configured LocalSystem.
Direct owner queries for the system-side processes were unavailable; configuration is not a
verified token-owner result. OpenClaw PID 15700 and its client chain remain under the current
Windows user. wslhost PID 4980's arguments associate that chain with OpenClawGateway.

The owner-terminated collector parent PID 28432 is absent. Its old client PID 24704 and that
client's child PID 7536 still exist under the current Windows user, with creation times matching
the Administrator attempt. Their elevated arguments remain unreadable. No client was stopped.

The snapshot proves Windows component/ownership metadata, **not current Linux broker health**.
It cannot establish an exclusive VHDX lock, pending transaction ownership, or that OpenClaw
caused the abort. Exiting the OpenClaw launcher before a targeted distro restart is a precaution
against lost jobs/reconnects. Terminating its distro would necessarily interrupt its Linux workload.
No non-interrupting Linux init repair has been established; interruption is not proved universally
necessary for every conceivable recovery.

Reproduce only the bounded Windows metadata inspection, without elevation or a WSL launch:

```powershell
.\.venv\Scripts\python.exe scripts/inspect_wsl_windows_metadata.py
```

This fixed-query tool has a 15-second worker deadline and a separate two-second cleanup deadline.
On timeout it may end **only its own newly created metadata PowerShell worker**; it never targets
an enumerated process or starts WSL. Partial JSON records survive a timeout; full command lines,
owner names, event messages, environment variables and stderr text are excluded. Historical PIDs
are read-only observations and must never be reused as an instruction to stop a process.

[Sanitized ownership evidence](../evidence/pc-wsl-process-ownership-2026-10-31.json) records the
snapshot and unchanged hashes of the original saved Administrator inputs. The six historical
crash reports were reanalyzed offline; no additional raw memory was collected.

[The reviewed proposal](pc-wsl-recovery-proposal.md) describes a maintenance-window recovery
candidate for **OpenClawGateway only**, after saving OpenClaw work and separate explicit approval.
It stops no other distro, edits no registration, and does not request a Windows reboot,
WSL-wide shutdown, reinstall, update, reset or virtual-disk deletion.

A targeted stop would still interrupt OpenClaw's Linux processes, so it has not been performed.
No non-interrupting in-place broker repair has been verified. The existing orphan client is
not killed blindly; live clients and queued requests can interact with the init failure.

After any separately approved recovery, require actual Linux echo/uname/id and a fresh
reconnected command, plus OpenClaw's real health and unchanged registration. Status alone
does not meet acceptance. If a recovery command hangs, do not escalate to broad restarts
or recreate the same collector loop.

## Work completed without WSL

The offline analyzer and regression checks proceed on Windows while the recovery proposal
remains unexecuted. Tests cover incomplete collection, event-query classification, input-size
and path bounds, redaction, and rejection of false completion/health claims. A process-spawn
sentinel verifies that analyzing saved evidence launches nothing.

At checkpoint 97af028, Ruff/format, mypy (25 application modules), and the full backend suite passed:
**253 passed, five environment skips, 95.41% statement coverage**. The five skips are four
unconfigured local PostgreSQL cases and one Windows symlink-privilege case. Nine diagnostic
tests passed. The retired PowerShell file was parsed only, never executed. No UI code changed.
The subsequent metadata-tool tests cover its two distinct finite waits, preservation of partial
evidence, bounded output parsing, and separation of metadata completion from Linux validation.
The ownership follow-up passed the full Windows backend suite: **257 passed, five environment
skips, 95.41% coverage**, plus all 13 diagnostic tests, Ruff/format (77 files), and mypy
(25 application modules). No frontend code changed; its production build was not repeated.

The application, provider adapters, approval gates, deterministic fixture engine and worker
contracts remain intact. Private execution/publication remain disabled. The experimental
sandbox and failure evidence in PR #8 remain preserved at 37c01e9.

## Separate worker assessment remains conditional

D: has substantial free space, but earlier available-RAM samples were below 0.5 GiB on this
8 GiB PC. No concurrent model/app/worker capacity was proved. A separate WSL2 distro shares
the VM/kernel and is not a hostile-code isolation boundary by itself.

Only after reliable Linux execution and measured capacity: review a distinct new D: worker
installation, non-root identity, distro-specific Windows-mount/interop separation, a compatible
reviewed sandbox and all six resource/network/filesystem/lifecycle probes. Do not change
OpenClaw's configuration or activate a host fallback to advance the demonstration.

[Sanitized follow-up](../evidence/pc-wsl-offline-review-2026-10-31.json) ·
[Historical PC measurements](../evidence/pc-wsl-diagnosis-2026-10-31.json) ·
[Official WSL commands](https://learn.microsoft.com/en-us/windows/wsl/basic-commands).
