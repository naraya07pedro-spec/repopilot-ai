# Local isolation alternatives — 1 November 2026

Current prerequisite work is recorded in [Hyper-V worker readiness](hyperv-worker-readiness.md).
The owner reopened read-only preparation and made a future Administrator request conditional
on verified readiness. No VM operation is authorized. The new host admission check denies RAM
pressure, and the full 512 MiB candidate allowance is unqualified in a 512 MiB guest. The
following records the earlier evaluation/code-only checkpoint; its no-download statements
describe that earlier checkpoint, not the newer media-integrity work.

The owner authorized evaluating alternatives on the existing 8 GiB Windows PC. WSL recovery
remains deferred; OpenClaw, existing VMs/disks, Windows security settings and main are preserved.
The verified local model and owner dispatcher are reused unchanged. No worker has passed live
isolation acceptance. Private execution and publication remain disabled.

## Owner decision: code preparation only

The owner chose **"Prepare code only; no elevated VM operations."** UAC and elevated VM work
are not authorized. No OS image/tool payload download or live VM test is being started.
The lifecycle template now blocks Create, Start, Inspect and Cleanup unconditionally before
token checks, module loading, filesystem checks or VM APIs. Plan remains available. This block
also applies to an Administrator; there is no CLI/environment bypass. The remaining template
is retained as reviewable code only. Revisit authorization only if the owner reopens the decision.
The Windows CLI guard test passed for Plan and all four blocked modes, with Hyper-V remaining
unloaded. Follow-up regression checks passed: 300 tests, five environment skips, 95.55%
coverage; Ruff/format and mypy passed. No live isolation probe ran.

## Actual eligibility snapshot

The read-only Windows inventory found Hyper-V and its PowerShell management module enabled,
vmms running, and 12 logical CPUs. Get-VM failed with a permission-related VirtualizationException;
this does not prove that Hyper-V or any VM is broken. Windows Sandbox, Windows Hypervisor Platform
and Windows Containers are disabled. WindowsSandbox.exe is absent. QEMU, Docker and VirtualBox
were not found on PATH or in the inspected common installation paths.

Visible RAM was 8,453,820,416 bytes; available RAM at the snapshot was 1,026,154,496 bytes
(about 979 MiB). D: had 138,294,800,384 bytes free; C: 5,655,957,504. Memory changes over time.
No existing VM configuration was enumerated successfully or changed. No WSL command was invoked.

## Comparison

| Strategy | Fit and current blocker | Decision |
| --- | --- | --- |
| Dedicated Hyper-V Linux guest | Hypervisor/tools enabled. Keeps the Linux UID/cgroup contract inside a separate kernel. Needs elevated access, a hardened guest/controller and enough RAM. | Preferred prototype to evaluate; not a validated worker. |
| Windows Sandbox | Disabled. Documented 2,048 MB minimum even if a lower memory value is requested. Its Windows guest does not directly satisfy the Linux UID/cgroup profile. | Do not enable/install/restart Windows for it under this task. |
| AppContainer + Job Objects | Recognized Windows boundary. Needs a distinct Windows identity/profile, filesystem review and demonstrated hard storage quota in addition to process limits. | Not a drop-in Linux-contract implementation; no host executor added. |
| QEMU hardware acceleration | Not installed; WHP disabled. Needs a reviewed accelerator/build and host resource controls; guest RAM alone is not a host-process memory cap. | No installer, feature change or accelerator fallback. |
| QEMU software TCG | Upstream excludes TCG from its guest-isolation security guarantees. | Rejected for untrusted execution even if some probes pass. |
| Docker/VirtualBox/rented host | Not installed/authorized; adds drivers, large images or cost, with separate compatibility requirements. | Not pursued. |

Sources: [Hyper-V prerequisites](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/get-started/create-a-virtual-machine-in-hyper-v),
[Sandbox minimum memory/configuration](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file),
[AppContainer boundary](https://learn.microsoft.com/en-gb/windows/security/book/application-security-application-isolation),
[Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects),
[QEMU security policy](https://www.qemu.org/docs/master/system/security.html),
[official Windows QEMU distribution links](https://www.qemu.org/download/).

## Concrete prototype and limits

[The proposal](../deploy/hyperv-worker.proposal.json) describes a new, disposable, diskless Linux
VM under D:\Projects\repopilot-local\hyperv-worker: 512 MiB fixed RAM, one vCPU, no network
adapters, host shares or drive passthrough. Controller authentication stays outside the guest.
Run model and worker sequentially; full concurrent capacity is unproved. Start requires at
least 1,536 MiB available host RAM. The proposed running-RAM watchdog is not yet implemented.

The reference Alpine Virtual ISO is version 3.24.3, 70,254,592 bytes, with published SHA-256
pinned. It is **reference boot media, not a prepared worker image**. Python/pytest/Ruff, verified
offline packages, a restricted guest launcher, cgroups and bounded writable mounts are still
needed. No ISO/package payload was downloaded or installed. The proposed download cap is
192 MiB; exceeding it needs a revised plan. See [Alpine downloads](https://alpinelinux.org/downloads/).

The lifecycle template uses a new Generation 1 BIOS guest for this small reference ISO. That
guest has no Secure Boot capability; host Secure Boot is unchanged. This explicit prototype
limitation is not signed-boot attestation. Existing guest firmware/security is untouched.
Production image/boot policy still requires review.

scripts/hyperv_probe_vm.ps1 defaults to Plan. Earlier Plan/AST checks and command-parameter
inspection passed. The current CLI guard test invokes all five mode names, but non-Plan modes
stop at the code-only block without loading Hyper-V. Their lifecycle bodies have **not** been
executed or live-validated. The retained template scopes operations to a new GUID-named VM and
configuration directory, checks no-network/no-disk settings, and retains ISO/state/evidence.
It does not run jobs, enable a gate or claim isolation. Unexpected failures require inspection;
never blindly repeat VM creation or broaden cleanup.

The owner declined per-run Administrator UAC and selected code-only preparation. No UAC,
VM creation/start/stop, feature/security change, WSL restart or paid operation ran. No persistent
administrator-group membership or service installation is proposed.

## Preserved probes and truthful evidence

The six source payloads from PR #8 at 37c01e9 are preserved byte-for-byte in the packaged
worker_probes.json catalog. Original test file SHA-256:
d06b58c4970c7aaf459fd397f5b645a4f7282f56e8af9aa2e23664f5ef6134f2.
Catalog and individual payload digests are pinned. Neither PR #8's runtime nor its failed
evidence was replaced. repopilot.isolation_probes creates data-only VerificationJob instances
using the existing Linux contract; it contains no subprocess or host-code executor.

The assertion layer checks guest-start observations, exact UID/kernel limits, zero host shares/
adapters, read-only guest root, receipt identity and confirmed cleanup. Boot failure is not a
memory-limit pass; a timeout kill is not OOM enforcement. CPU acceptance requires a positive
throttling delta. Cancellation must occur after guest execution starts. Observation schemas do
not prove that their producer is honest. Synthetic positives never authorize activation;
the production DisabledWorker gate remains unchanged.

The future backend must execute all six probes inside its guest and independently observe
results from a trusted controller. Also demonstrate controller-crash recovery, no surviving
owned VM/process/job state, no automatic execution replay and no lost/forged receipts. Booting
Linux or matching configuration JSON is not a security pass.

Local code validation passed: **299 tests, five environment skips, 95.50% statement coverage**;
Ruff/format (85 files) and mypy (27 application modules) passed. The 22 new assertion tests are
synthetic and launch no guest. An offline wheel build preserved the exact pinned catalog hash.
One initial full-suite run recorded TimeoutExpired in an existing fixture-preparation test;
its targeted rerun and the final full suite passed with no source/timeout/limit changes. Both
logs are retained on D:. This is application verification, not a live sandbox pass.

The earlier rootless runsc/cgroup failure is preserved in PR #8. A fresh guest does not make
that failing runtime compatible. Full-VM isolation needs its own reviewed guest restrictions
and live evidence; no privilege, cgroup, network or resource-limit bypass was introduced.

## Remaining blockers and owner-only actions

1. Elevated prototype work is deferred by the owner. A new owner instruction is required to
   reopen it; do not repeat the approval request. Windows denies this session VM management.
2. Any future authorized live test will need enough RAM headroom without interrupting OpenClaw.
   No application closure or guard reduction is part of the current code-only work.
3. Engineering must still build/harden the guest and controller, run all live probes, and prove
   cancellation, cleanup and crash recovery. The new assertion tests do not complete this work.
4. This process has no GITHUB_APP_ID, GITHUB_INSTALLATION_ID or GITHUB_APP_PRIVATE_KEY_FILE
   configuration. This is presence evidence; no credential files were searched. Once isolation
   is verified, configure repository-scoped App authorization locally using the
   [activation instructions](owner-activation.md). Never paste a key into chat or Git.
   Development pushes do not validate the App.
5. Then use the verified local model, inspect/approve the exact one-file candidate, run isolated
   checks, separately approve publication, and reconcile the real draft PR in
   naraya07pedro-spec/repopilot-ai. That acceptance has not happened.
