# Targeted WSL recovery proposal — approval required

No recovery command in this document has been executed. The live diagnostic collector is retired
and must not be rerun. This plan does not authorize service restarts, Windows reboot, WSL shutdown,
installation, registration changes, or disk removal.

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

The proximate WSL failure is a repeatedly aborting init/interop broker; live broker state and
the original disconnecting client remain unverified. A new live collection loop is not justified.
No raw core memory or event-message body is published in the repository.

## Safest narrow recovery candidate

This would briefly interrupt OpenClaw and therefore requires **separate explicit approval**.
It is a recovery candidate, not a proven local cure. The owner's read-only Administrator approval
does not extend to this operation.

1. Agree an OpenClaw maintenance window. Save active jobs and use OpenClaw's normal shutdown
   controls. Confirm its Windows launcher will not automatically reconnect/relaunch the distro.
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
5. Once the distro is confirmed stopped and its VHDX is no longer open, an approved backup step
   may preserve the unchanged disk on D: and verify the copy before booting it again. A live
   VHDX copy is not a consistency-verified backup. D: is on the same physical SSD, so this is
   local rollback protection, not independent media. No export/import or restore is authorized.
6. Start only the existing distro and validate an actual fresh Linux process:

   wsl --distribution OpenClawGateway --user root --cd / --exec /bin/echo repopilot-wsl-ok
   wsl --distribution OpenClawGateway --user root --cd / --exec /bin/uname -r
   wsl --distribution OpenClawGateway --user root --cd / --exec /usr/bin/id

   Require exit 0 and expected output. Repeat a fresh echo after reconnecting; status/list alone
   is insufficient. If a call stalls, do not run a kill-on-timeout wrapper or the retired collector.
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
