# Hyper-V worker preparation — 1 November 2026

**Not ready for an elevated VM run. No VM was created, started, stopped or removed.**
The owner reopened prerequisite preparation, conditional on verification before a new
Administrator request. That condition is not met. Both the unconditional code-only
lifecycle guard and the production `DisabledWorker` remain in place. WSL diagnostics,
OpenClaw, the verified model/dispatcher, main and PR #8 are untouched.

## Measured host eligibility

This PC runs Windows 11 Pro, build 26200, on a Ryzen 5 4500 (6 cores/12 logical CPUs).
Visible physical RAM is 8,453,820,416 bytes. Firmware virtualization and the running
hypervisor were confirmed. `vmms` is Running and Hyper-V PowerShell commands exist.
Pro is a supported Hyper-V edition; this does not certify a particular Alpine guest.
See Microsoft's [requirements](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/system-requirements-for-hyper-v-on-windows)
and [edition compatibility](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/get-started/install-hyper-v?pivots=windows).

The first read-only inventory returned InstallState=1 for Hyper-V and its management
PowerShell feature. Later **bounded** optional-feature queries timed out; their failures
are retained rather than reported as successful checks. The final collector keeps the
other successful facts when this query fails. No feature/role change was attempted.
Existing VM inventory was not repeated: this session's earlier permission denial remains
an explicit limitation. A future authorized controller must inventory existing VM IDs
read-only and verify they remain unaffected.

C: and D: are NTFS partitions 3 and 5 on the same physical Disk 0, a 512,110,190,592-byte
RX7 SATA SSD. The 30.735-second sampling window found:

| Metric | Observed |
| --- | --- |
| Available RAM | 375.21–724.00 MiB |
| Lowest commit headroom | 7,690.43 MiB |
| Highest commit usage | 76.44% |
| Highest sampled total CPU use | 61.86% |
| C: free at end of window | 4.994 GiB |
| D: free at end of window | 128.766 GiB |
| Known llama.cpp/Ollama executable names | None found |

**Resource admission failed because RAM was below 2,048 MiB.** Known process-name absence
does not exclude every possible inference runtime; an exclusive model/worker lease is
still required. No application was closed. These measurements include ordinary host
activity and preparation overhead; they are not an idle-machine benchmark.

`scripts/hyperv_preflight.py` uses native read-only Win32 memory/commit/CPU counters,
samples 16 times across at least 30 seconds, and wraps its PowerShell inventory in a
25-second child timeout. CIM calls have five-second operation limits. The only process
it can kill is its own timed-out read-only child. It invokes neither WSL nor VM APIs.
Its optional report output uses exclusive file creation. The first sampling version
fell just short of 30 seconds because of scheduling jitter and correctly failed; the
fixed scheduling window and both reports are retained on D:.

## Fixed RAM and one-vCPU assessment

One vCPU can schedule the existing sequential Python checks; guest driver support,
latency and peak RAM remain unmeasured. **Booting a small Linux ISO is insufficient
evidence that the complete worker fits.** The existing job contract defaults to a
512 MiB candidate cgroup. A fixed 512 MiB VM must also hold the kernel, tool pages,
trusted controller and filesystem bookkeeping. A cgroup maximum can be set larger
than usable memory, but global guest OOM could then occur before that limit. We
cannot promise the complete candidate allowance or call that reliable enforcement.

The planning code reserves 128 MiB for OS/tools/controller and 64 MiB safety margin.
These are conservative **engineering reservations, not measured Alpine requirements**.
The default 512 MiB candidate fails that budget; a 128 MiB candidate fits the static
reservation but is **not runtime-qualified**. No job defaults, probe limits, candidate
profile or approval digest were changed. Only the existing memory probe requests
128 MiB; the other preserved phases still request 512 MiB.

Before a complete 512 MiB worker can be promised, implement and independently qualify
an explicit smaller candidate profile with the current source and approval contracts,
then measure boot/idle/peak workload RAM and controller survival. Alternatively, a
larger VM would need separate owner authorization; it is outside this 512 MiB plan.
Neither swap, dynamic memory nor weaker OOM assertions is a workaround.

## Image and controller review

The pinned reference source is the official Alpine Virtual 3.24.3 x86_64 ISO:
[publisher directory](https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/x86_64/).
Expected size is 70,254,592 bytes; SHA-256 is
`cdc1bc0efc64d8d611bf3733f54868172a545888dfd726f518bf279bcb0ff1af`.
The adjacent publisher `.sha256` was fetched again over HTTPS and matched the pin.
The complete local ISO was independently hashed again after download; size and digest
matched. Read-only archive listing found 123 entries, BIOS/EFI boot files, kernel,
initramfs and modloop, but no Python/pytest/Ruff APKs. The included kernel configuration
enables cgroups, memory/PID controls, CFS bandwidth, namespaces and Hyper-V support;
that is static compatibility evidence, not a boot or effective-limit observation.
`scripts/prepare_hyperv_media.py` permits only this URL/origin, refuses replacement
of existing files, verifies complete bytes before rename, retains failed partial
files and caps its D: media directory at 192 MiB. It has socket/elapsed bounds and
does not install, extract, execute or boot any media. The evidence records the actual
download result separately. Matching a publisher hash is **not** PGP signature,
Secure Boot, immutable-root or worker-image attestation.

This remains reference boot media. The image builder, verified offline Python/pytest/
Ruff tool manifest and hardened trusted guest launcher are absent. Alpine's documented
[stock setup](https://docs.alpinelinux.org/user-handbook/0.1a/Installing/setup_alpine.html)
permits root login; `setup-alpine` is not the restricted UID-65532 worker launcher and
must not be used as one. Do not run its network/disk installation helpers here.

The retained Generation 1 BIOS proposal has no guest Secure Boot capability; no host
security control or other VM's firmware is changed. This limitation needs explicit
image policy review. No signed-boot assertion is made.

The lifecycle template has now been tightened for eventual review: durable unique
creation intent before `New-VM`, saved exact VM ID after creation, folder/name UUID
binding, no NIC/VHD, disabled checkpoints/automatic start/integration services, and
explicit checks of those settings. Microsoft documents
[integration service control](https://learn.microsoft.com/en-us/powershell/module/hyper-v/disable-vmintegrationservice).
All mutation bodies remain unreachable. A second guard refuses Start even if the
outer code-only guard were mistakenly removed while the controller remains unbuilt.

The Python admission and qualification code is **not a VM controller**. Still needed:
an independent bounded host watchdog, exclusive runtime lease, ACL-restricted serial
transport, immutable guest root, trusted cgroup-v2/namespace launcher, strict bounded
job protocol and host-owned receipt signing. Provider/App/controller keys never enter
the guest. Candidate stdout and serial messages are data, never shell commands or
activation authority. Required boot attestation includes tool/image/controller digests,
trusted challenge response, UID, root mount flags, kernel limits and absence of channels.

## Admission and emergency-stop specification

The typed policy in `repopilot.hyperv_preparation` implements the following **decision
checks**, with synthetic tests. It is not connected to a VM stop/start loop:

| Stage | Required measurement/action |
| --- | --- |
| Start | Fresh contiguous 30-second window; gaps at most 3 s; last sample age at most 3 s |
| Start RAM | Every sample at least 2,048 MiB free physical RAM and 2,048 MiB commit headroom |
| Start CPU/commit | Every sample at most 80% total CPU and 85% commit usage |
| Disk | At least 4,096 MiB free on both C: and D:; no storage changes to obtain it |
| Concurrency | No known model runtime; additionally require a controller-owned exclusive lease |
| Running telemetry | Sample every second; unknown/stale heartbeat over 3 s aborts only the owned VM |
| Critical RAM | Below 512 MiB: immediate owned-VM abort |
| Sustained pressure | For 5 s: RAM below 768 MiB, commit over 90%, or CPU over 95% causes owned-VM abort |
| Overlap/disk failure | Model overlap/unknown state or disk threshold failure aborts only the owned VM |
| Hard lifetime | Independent supervisor stops the exact owned VM within 600 s; not implemented yet |

The host continues running Windows, Codex and OpenClaw. No policy action is allowed to
close them, stop another VM, restart a service, shut down WSL or reboot Windows. A
watchdog must remain effective when the primary controller crashes, and must be tested
before candidate execution. A heartbeat policy alone is not that implementation.

## Six real probes and fail-closed sequence

The byte-pinned PR #8 catalog and existing `assess_probe` contract are reused unchanged.
`qualification_plan()` creates review-only jobs, never executes their Python and never
authorizes a worker. Its ephemeral leases must be regenerated after a future authorization.

| Case | Required real guest evidence |
| --- | --- |
| Benign checks and teardown | Actual pytest, Ruff lint and format succeed; job cgroup empty and mounts cleaned |
| Filesystem/identity/network/secrets | UID 65532, mode-700 owned workdir, readonly root, forbidden writes denied, no host sockets/keys, outbound and metadata connections fail; host confirms zero NICs/shares |
| Disk | 80 MiB attempted write fails ENOSPC/EDQUOT under the exact 64 MiB writable budget |
| Memory | 1 GiB attempt within a 128 MiB cgroup produces MemoryError or exit 137 with positive OOM-kill delta; boot failure/global OOM/timeout does not pass |
| Processes | 64-child attempt is stopped below 64 by pids.max=32; no surviving children |
| CPU/deadline/cancellation | cpu.max matches 250m, throttling counter increases and five-second deadline stops the loop; separate phase cancels only after trusted process-start observation and stops within 30 s |

All cases also require exact receipt run/nonce/job-digest binding, effective kernel
memory/swap/CPU/PID observations, trusted guest-start observation and confirmed cleanup.
The plan orders authorization → resource admission → digest checks → existing-VM
inventory/unique intent → create Off/save ID → independent watchdog → inspect effective
settings → bounded boot/attestation/RAM measurements → sequential probes → cleanup →
controller-loss recovery → exact VM removal and inventory comparison. First unknown,
failure, missing evidence or pressure stops dispatch and invalidates acceptance. No host,
WSL, fixture or weaker sandbox fallback is permitted. Synthetic positives authorize nothing.

## Teardown and recovery procedure

1. Stop dispatch and retain immutable run ID, intended name, D: folder, VM ID, media and
   controller digests, journal and bounded logs. Do not automatically recreate or replay.
2. Stop/kill only the guest's job cgroup; prove zero survivors and unmount its writable
   storage. If transport/controller fails, the independent host watchdog must stop only
   the exact new owned VM. Failure to confirm stopping is an unresolved run, never a pass.
3. Reconcile exact saved VM ID + GUID name + GUID folder under the fixed D: root; reject
   reparse points, unexpected VHDs, checkpoints or ownership ambiguity. An intent without
   an ID requires owner review, not wildcard cleanup or blind creation retry.
4. Confirm the owned VM is Off, remove exactly its registration/configuration, then verify
   absence and compare the existing VM inventory. Never pipe wildcard name matches to
   removal, operate on WSL disks or change unrelated VM settings.
5. Retain ISO, state, intent and evidence. No recursive filesystem deletion is in scope.
   Microsoft's [Remove-VM behavior](https://learn.microsoft.com/en-us/powershell/module/hyper-v/remove-vm)
   deletes configuration and can merge checkpoints; therefore unexpected checkpoints/
   VHDs block this template instead of being removed.

This is the complete proposed procedure, **not live teardown/recovery proof**. The template
and future supervisor still need real fault-injection validation. Preserving ambiguous
state for owner inspection is preferable to broadening cleanup. Rollback for an authorized
future run consists solely of stopping/removing this exact disposable VM; retained evidence
needs no restoration, and existing VMs/disks/configurations require no rollback.

## Next prerequisite and owner-only boundary

Finish the offline hardened worker image, trusted guest/serial controller, independent
watchdog and smaller explicit candidate profile; verify their digests and executable test
coverage. Recheck sustained host RAM only when appropriate. Then present **one** per-run
Administrator request bound to reviewed code/media hashes, one generated VM identity,
512 MiB/one vCPU, D: paths, no channels and a ten-minute maximum lifecycle. Do not request
it now: RAM, image/controller readiness and the full default memory contract remain blocked.

Only a genuine local model → owner approval → isolated tests → separately approved draft
PR with repository-scoped GitHub authorization can complete acceptance. None occurred here.

## Local verification

Ruff check/format and strict mypy passed. The new admission, planning, media-integrity and
Windows code-only guard tests passed; they launch no guest and are not security acceptance.
The first full suite encountered one existing `test_plan_tampering` preparation failure;
its saved SQLite run records `TimeoutExpired` before check results or an approval digest.
The focused C: retry reproduced it. A retry with only this process's TEMP/TMP on D: passed
in 2.12 seconds; no application code, timeout, approval or resource limit was changed.
The full-suite D: rerun and exact results are recorded in the preparation evidence.
That rerun passed **325 tests, five environment skips, 95.67% coverage** in 169.23 seconds.
Keep future test temporary files on D: using per-process TEMP/TMP; do not change unrelated
application settings or delete the preserved failed test data.
