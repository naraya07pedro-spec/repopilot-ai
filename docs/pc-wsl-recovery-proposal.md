# Targeted WSL recovery proposal — approval required

No recovery command in this document has been executed. The live diagnostic collector is retired
and must not be rerun. This plan does not authorize service restarts, Windows reboot, WSL shutdown,
installation, registration changes, or disk removal.

## Owner decision — 1 November 2026 (Asia/Jakarta)

The owner chose: **"Keep OpenClaw running; defer recovery."** The targeted maintenance
proposal below remains unexecuted and is not authorized. Leave OpenClaw, its distro and WSL
services running; do not restart Windows. Do not repeat the retired collector or terminate
the historical diagnostic clients. Revisit interruption only if the owner reopens that decision.
Windows-only RepoPilot engineering and verification may continue with private execution disabled.

## Specific failures established from saved evidence

1. The six saved real-core reports identify WSL init PID 2 aborting with SIGABRT and the exact
   Broken pipe exception at SocketChannel.h:183 (SendMessage). This is consistent with the
   WSL 2.7.11 init/interop reply failure reported in [upstream issue #41592](https://github.com/microsoft/WSL/issues/41592).
   That issue is corroboration, not a verified permanent fix or proof of the initiating client here.
2. The Administrator collector wrote its event-query output at 21:47:38 local time. All four
   selected channels had no matching events in the last-24-hours / levels-1-to-3 selection.
   The old collector represented this as read_completed=false. It is not an access-denied result,
   and the limited absence does not establish VM health or exclude a Linux-side abort.
3. At 21:48:04 it recorded client PID 24704 past the 25-second deadline. The old code then called
   WaitForExit() without a timeout. This explains why PowerShell PID 28432 stayed stuck.
   No admin-result.json was saved, so later compute inventory and actual Linux validation were
   never completed. Client arguments were not saved, so the evidence cannot identify whether
   the stalled call was metadata enumeration or the debug shell.
4. The owner terminated PowerShell PID 28432. A subsequent metadata-only process query found
   its WSL child PID 24704 still present with parent PID 28432. Its elevated command line was
   not readable from the current token. It was left untouched. This is a snapshot, not a promise
   that the PID will still refer to that process later.

The proximate WSL failure is a repeatedly aborting Linux init/interop process. The original
disconnecting client and current Linux broker health remain unverified. The Windows WslService
process is a different component: its Running state does not establish that Linux init survived.
No raw core memory or event-message body is published in the repository.

## Is OpenClaw a recovery blocker?

There is **no evidence that OpenClaw causes or blocks recovery**. The current bounded Windows-only
snapshot confirms this existing process chain under the current Windows user's account:

OpenClaw.Tray.WinUI.exe (15700) -> wsl.exe (23368) -> wsl.exe (21196) -> wslhost.exe (4980).

The last process has OpenClawGateway's registration ID in its readable arguments. That establishes
association, not Linux gateway health, an exclusive disk lock, a queued broker request or causality.
The diagnostic leftovers are a separate chain: absent PowerShell 28432 -> wsl.exe 24704 ->
wsl.exe 7536. Both WSL clients belong to the current Windows user, but their arguments are
unreadable from this non-elevated session. Their PIDs/creation times were recorded, not targeted.

WslService PID 4660, vmcompute PID 1288, hns and HvHost report Running / service exit code zero,
with LocalSystem as their configured service account. Direct process-owner queries for
WslService/vmcompute/vmmemWSL return code 2; actual token ownership is not independently readable.
The remaining user-owned WSL host/relay processes do not prove that Linux init accepts sessions.

Closing OpenClaw's **Windows launcher first is a precaution** to save work and prevent a reconnect
race, not a demonstrated technical prerequisite imposed by WSL. In contrast, the proposed
**distro termination itself necessarily interrupts OpenClaw's Linux processes** because the
affected init belongs to that same distro. It has not been proved that every possible recovery
requires interruption, but no non-interrupting repair is established by the available evidence.

The upstream maintainer links [exception handling fix #40691](https://github.com/microsoft/WSL/pull/40691)
and a zombie-state fix in [issue #41592](https://github.com/microsoft/WSL/issues/41592), reporting
them in pre-release versions and not backported to 2.7.x at the time of that comment.
The exception-handling PR is merged upstream; this is not proof it is installed here or a reason
to update this shared environment without review. No update or pre-release installation is proposed.

## Safest narrow recovery candidate

This would briefly interrupt OpenClaw and therefore requires **separate explicit approval**.
It is a recovery candidate, not a proven local cure. The owner's read-only Administrator approval
does not extend to this operation.

1. Agree an OpenClaw maintenance window. The owner saves active jobs and uses OpenClaw's normal
   controls to pause/exit its launcher. Confirm it will not automatically reconnect/relaunch the distro.
   Do not kill arbitrary node.exe, python.exe, wsl.exe, or service processes.
2. Record the exact OpenClawGateway registration and original VHDX location. Do not change
   registration, default user, credentials, mounts or application settings.
3. With explicit interruption approval, target only this distribution:

   wsl --terminate OpenClawGateway

   Microsoft's [command reference](https://learn.microsoft.com/en-us/windows/wsl/basic-commands#terminate)
   defines this as stopping the named distribution. It stops its Linux processes; unsaved work
   must already be saved. It does not request unregister/reset or delete its virtual disk.
   Do not substitute wsl --shutdown or a WslService/vmcompute restart.
4. If that command hangs or fails, stop escalation and retain the evidence. Do not repeatedly
   launch clients or force-close them on an automatic timeout. Broader recovery would need a
   new reviewed proposal and separate approval.
5. There is no configuration or disk migration to roll back. Resume by launching the original
   registered distro, then reopening OpenClaw normally. Termination cannot restore unsaved process
   memory, which is why saving jobs first matters. If validation fails, preserve evidence and stop;
   do not turn a failed restart into a reset, reinstall or backup restore.
   An optional separately agreed backup is possible only after a confirmed stop and unlocked VHDX:
   copy the unchanged disk to D: and verify the copy. A live VHDX copy is not consistency-verified;
   C: and D: share one SSD. No export/import or restore is authorized by this proposal.
6. Start only the existing distro and validate an actual fresh Linux process:

   wsl --distribution OpenClawGateway --user root --cd / --exec /bin/echo repopilot-wsl-ok
   wsl --distribution OpenClawGateway --user root --cd / --exec /bin/uname -r
   wsl --distribution OpenClawGateway --user root --cd / --exec /usr/bin/id

   Require exit 0 and expected output. Repeat a fresh echo after reconnecting; status/list alone
   is insufficient. Observe each approved WSL call for a bounded interval and, if it stalls,
   return a pending record without killing its client or waiting indefinitely. Launch no additional
   call while one is pending. Do not run the retired collector or a kill-on-timeout WSL wrapper.
7. Reopen OpenClaw normally and verify its real health, saved work, original registration and
   unchanged disk/configuration. Save timestamps and exact Linux exit codes. Keep all backups.

No permanent remediation is claimed by a successful restart; recurrence needs reviewed upstream
evidence. No low-risk, non-interrupting in-place broker repair has been established.

## Work that proceeds independently

The offline analyzer reads only saved bounded JSON, never invokes WSL or another process,
distinguishes filtered-empty events from permissions errors, flags missing completion data,
and does not print raw event messages or grant execution permission from evidence fields.
The old live collector now fails closed without launching anything.

Application, provider, approval and worker-contract checks remain executable on Windows.
Private execution/publication remain disabled. A new worker distro on D: is deferred until
reliable Linux execution and sufficient concurrent memory are actually verified.
