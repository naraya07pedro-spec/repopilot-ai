# PC WSL E_UNEXPECTED diagnosis — 31 October 2026

Status: **real Linux execution is still failing**. This diagnosis does not claim recovery,
a working isolated worker, or a verified WSL configuration fix. No service/distro restart,
Windows reboot, registry change, distro reset/reinstall/relocation/removal, or sandbox bypass ran.

## What is actually established

The PC has Windows 11 Pro build 26200, WSL 2.7.11.0 and reported kernel 6.18.33.2-2.
VirtualMachinePlatform, the WSL optional feature and the Hyper-V hypervisor feature report enabled.
Firmware virtualization and the active hypervisor report true. WslService, vmcompute, hns and
HvHost are running with no service exit errors. The WMI SLAT boolean reports false under the
active hypervisor; this is not evidence that this Ryzen 5 4500 lacks the capability.

Only OpenClawGateway is registered: WSL2, default UID 0, reported Running, original C: storage.
Its VHDX remains about 4.64 GiB and the OpenClaw Windows process remains running. Neither the
registration nor virtual disk was altered. C: retains roughly 6.3 GiB free following separately
approved package-cache cleanup; D: has about 129 GiB. Available RAM snapshots fell below
0.5 GiB during this audit, so concurrent capacity remains a material limitation.

Actual /bin/true and /bin/echo launches return Wsl/Service/E_UNEXPECTED. Explicit distro,
root user and Linux cwd do not help. A terminal/ConPTY launch also fails. No missing executable
or Windows-path-only explanation was established. wsl --status/list succeeds but is not a
Linux execution test.

Six existing crash dumps were inspected for bounded ELF note metadata. All are genuine
ELF cores identifying the init-systemd(Op... process, PID 2, with SIGABRT (6), signal code -6.
The most recent file was modified at 09:31 local time on 31 October. This establishes repeated
WSL init self-aborts. A separate opt-in, size-bounded allowlist scan found the exact formatted
Broken pipe error at SocketChannel.h:183 (SendMessage) in all six files. Only that strict public
error/source-path pattern was emitted; adjacent bytes, arguments and environment were excluded.
This identifies the recorded internal exception but does not prove which client disconnected
or the current live broker state. Raw dump memory and credentials were not copied or printed.

The same-version [upstream init/interop abort report #41592](https://github.com/microsoft/WSL/issues/41592)
describes an init crash followed by failed new sessions while existing systemd work continues.
Its broken-pipe/init failure is consistent with the locally recorded exception. The particular
client disconnect and live failure chain remain to be confirmed; no shipped fix was verified.
The issue's closed state is not proof of resolution.
No speculative update, memory limit, networking mode or systemd flag was applied.

[Sanitized measurements](../evidence/pc-wsl-diagnosis-2026-10-31.json) record observed facts and
inferences separately. The fuller local reports and original dumps remain outside Git.

## Repeat the metadata-only core inspection

From the repository root with the locked Python environment:

```powershell
.\.venv\Scripts\python.exe scripts/inspect_wsl_crash_notes.py
```

An explicit --directory may select an existing local crash directory. The reader inspects at
most 32 files, limits ELF headers and note bytes, and never reads PT_LOAD memory segments.
Default output contains filename/size/time and allowlisted signal/PID/executable note fields only.
The explicit --known-exception option reads at most 1 MiB per core and emits only exact public
broken-pipe/source-path matches. It never prints adjacent memory or uploads anything.

## The next owner-only action: read-only Administrator diagnostics

The current Codex process is not elevated. Windows explicitly refused wsl --debug-shell,
hcsdiag list, and the Compute/Worker/HNS administrative event channels. An empty unelevated
event query must not be reported as evidence that no errors occurred.

The owner approved a read-only elevated collector. The Windows UAC launch reported that it was
canceled, and no elevated report directory was created. This is not a diagnostic result or a
denial from RepoPilot. The remaining owner-only action is to run the approved collector from an
Administrator PowerShell terminal:

```powershell
& 'D:\Projects\repopilot-ai\scripts\collect_wsl_admin.ps1'
```

The UAC request for this collector does **not** authorize any recovery interruption. No restart
approval has been given. A new security prompt will not be retried unattended after cancellation.

The collector writes a new report directory under D:\Projects\repopilot-local\wsl-diagnosis-2026-10-31.
An alternate D: output directory is accepted. It requires the selected distro to already be
reported running; it will not start a stopped distro. It reads service/registration/resource
metadata, bounded administrative event entries, compute inventory, and a fixed debug-shell
process-name/kernel-error selection. A client exceeding 25 seconds is recorded as pending;
its connection is retained without a forced termination. It then tries an
actual distro /bin/echo token; only exit 0 plus the expected token counts as success.

It does not stop/restart services, terminate a distro, enable log channels, edit wsl.conf or
.wslconfig, inspect credentials, copy raw cores, create a distro, change permissions, update WSL,
or alter OpenClaw. Local event messages and debug output must be reviewed before sharing;
they are not automatically safe for a public commit.

## Recovery decision after the Administrator report

First confirm whether the current VM still has its init/session broker and correlate the recorded
abort/interop exception with transport and memory logs. Record actual evidence before choosing
a remedy. Historic core contents cannot identify the initiating client or prove live process state.

If the init broker is gone, no non-interrupting restart or config-only cure has been verified.
Save OpenClaw state and request a separate narrow maintenance-window approval before any
targeted recovery. Do not silently run wsl --shutdown, restart WslService/vmcompute, terminate
OpenClawGateway, reboot, or substitute unregister/reset/reinstall commands. The current user
has explicitly withheld interruption approval.

After any separately approved remedy, require repeated actual Linux commands in the existing
distro, not status alone: /bin/echo, /bin/uname and a harmless process after reconnect. Verify
OpenClaw's real health and unchanged registration. Do not mark this document resolved until
those commands and application checks have actually passed.

## Conditional assessment for a separate RepoPilot worker on D:

No new distro is installed or approved by this assessment. Disk capacity on D: is nominally
adequate for a small new root filesystem, but real concurrent RAM headroom is not established.
A second WSL2 distro shares the WSL VM/kernel and does not by itself isolate hostile code.

Only after reliable Linux execution and sufficient measured capacity:

1. Inspect a new, unused D:\WSL\RepoPilotWorker destination and choose a distinct distro name.
   Use the installed WSL's supported --location/import mechanisms for a new distro, without
   moving or modifying OpenClawGateway. Installation would require its own reviewed scope.
2. Use a non-root worker identity and distro-specific Windows-mount/interop restrictions;
   do not alter the global settings or OpenClaw's wsl.conf. Verify the actual boundary,
   cgroup delegation and lifecycle behavior before any untrusted code is considered.
3. Preserve all six PR #8 isolation probes and failure evidence. The released gVisor defect
   is not cured by new storage or WSL boot. A reviewed compatible runtime and successful
   resource/network/filesystem/cancellation/cleanup/recovery acceptance are still required.
4. Keep the existing DisabledWorker and private publication gate closed. No cloud workers,
   paid model API or host-execution fallback is allowed.

## Validation scope

PowerShell parsing, real ASCII/UTF-16 child-client output handling and the non-admin guard were
checked locally. The full backend suite passed **248 tests, five environment skips, 95.41%
statement coverage**. Skips are four unavailable local PostgreSQL cases and one Windows symlink
privilege case. Ruff/format, mypy and the configured scan of 155 tracked files passed.
Elevated collection remains unperformed. Four Python diagnostic tests cover
metadata-only output, optional strict exception matching without adjacent private bytes, and
malformed/oversized note rejection. Full repository checks are recorded with the commit handoff.
These tests prove diagnostic behavior, not WSL repair or sandbox security.

[Official troubleshooting and log guidance](https://learn.microsoft.com/en-us/windows/wsl/troubleshooting).
