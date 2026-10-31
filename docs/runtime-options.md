# Runtime options and decision gate — 31 October 2026

No runtime will be implemented or activated until an eligible disposable test host is available.
No paid resource was provisioned or quoted. Existing hardware may avoid a new cloud invoice;
power, storage and operating effort still have costs. Provider/model API charges are separate.

| Option | Actual prerequisite and evidence | Cost and decision |
| --- | --- | --- |
| Reviewed compatible gVisor release | Rootless Linux, subordinate IDs, delegated cgroup v2 CPU/memory/pids; runtime must respect the delegation boundary or support user-systemd. Both released configurations failed before guest execution in PR #8. Upstream #13853 is open/unmerged as rechecked today. | Open-source runtime; no new infrastructure bill on existing suitable hardware. No known passing release/host combination was established. Wait for a reviewed compatible release and test it; do not install the unreviewed PR. |
| Dedicated Linux host/VM with gVisor | Existing disposable host, separate from private data and secrets, with outer resource caps, correct delegation, immutable tool image and a compatible runtime. Standard Ubuntu 24.04 + Podman 4.9.3 + runsc release-20261026.0 already failed despite successful delegation. A different host alone does not fix that runtime. | Existing hardware can avoid new rental charges. A rented host requires a specific quote and owner approval; no price or free tier is assumed. Host availability alone is insufficient evidence. |
| Properly isolated Firecracker microVM | Linux x86_64/aarch64, supported host/guest kernels, hardware virtualization and read/write `/dev/kvm`; patched host, reviewed jailer/seccomp/cgroup setup, per-job guest disk/lifecycle, bounded logs, no guest credentials and denied networking. KVM availability and isolation are unverified here. | Open-source VMM; no license purchase. Existing KVM-capable hardware may avoid new cloud rental. Cloud nested virtualization/bare-metal availability and price must be checked for a named host. Highest new implementation/maintenance effort; no adapter or deployment was started. |

Official evidence: [gVisor rootless modes](https://gvisor.dev/docs/user_guide/rootless/),
[production guidance](https://gvisor.dev/docs/user_guide/production/),
[upstream user-systemd change](https://github.com/google/gvisor/pull/13853),
[Firecracker prerequisites](https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md),
[production host/security requirements](https://github.com/firecracker-microvm/firecracker/blob/main/docs/prod-host-setup.md).

## Recommendation and acceptance procedure

Release the fail-closed application for portfolio review now; spend no money on a worker.
First prefer an already owned disposable Linux host plus a reviewed compatible gVisor release.
If no such combination is available, keep the agent blocked. A microVM is an alternative only
after an existing KVM-capable environment and a security review are available, not a speculative
replacement for the current runtime.

Before new runtime code: record host/kernel/runtime versions, user identity, cgroup delegation
and any required virtualization capabilities. Reject candidates that require rootful execution,
global cgroup write access, ignored resource errors, host networking or privileged host mounts.
Preserve the six [existing live probes in PR #8](https://github.com/naraya07pedro-spec/repopilot-ai/blob/37c01e9c6bb77b75940f4072aa8cf0974a8d8b37/tests/test_sandbox_live.py)
and their CPU/memory/PID/disk, filesystem/network, deadline and cancellation assertions.
Require actual guest execution, kernel limit/throttling evidence, teardown and live crash recovery,
then repeat full application CI. A guest startup failure is a failure, never a resource-limit pass.
Only synthetic fixtures are authorized for these tests; model/GitHub credentials stay outside.
