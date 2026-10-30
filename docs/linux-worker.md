# Experimental Linux worker: setup and validation

Implemented, **live validation attempted and blocked**. All six mandatory CI probes fail at
gVisor startup because its released systemd driver cannot create rootless user scopes. See the
[exact diagnosis, raw CI logs and dedicated-host procedure](sandbox-ci-diagnosis.md).
Windows cannot run this driver. Owner execution/publication remains closed; there is no bypass
switch. Controller tests mock Podman and do not prove hostile-code isolation. No worker is deployed.

## Target environment and trust boundary

Use a dedicated disposable Linux VM, preferably Ubuntu 24.04 LTS, with cgroup v2 delegation,
an unprivileged worker account, subordinate UID/GID mappings and rootless Podman. Install a
reviewed gVisor `runsc` release at `/usr/local/bin/runsc`; Podman is `/usr/bin/podman`.
This is the implementation's target configuration, not a claimed passing compatibility matrix.
Ubuntu 24.04 / Podman 4.9.3 / runsc release-20261026.0 with systemd cgroups was tested and fails;
a new host using the same combination is expected to reproduce the upstream issue.
Keep the VM separate from developer files and model/GitHub secrets. No Docker socket is used.

The worker account controls a pinned local image and private job journal. Candidate files are
bounded stdin data, staged by a trusted image entrypoint in ephemeral tmpfs. Each pytest/lint/
format command gets a fresh container. The driver requests non-root UID 65532, no network,
read-only root, no capabilities, no privilege escalation, bounded memory/CPU/processes, and
64 MiB total writable tmpfs. Automatic image pulls and inherited proxy/environment values are
disabled. It inspects effective runtime/user/network/resources/mounts before starting the check.

The controller records real exit codes/output and signs receipts outside the sandbox. Output,
time and cancellation are bounded; success cannot be returned before cleanup is confirmed.
The SQLite journal rejects duplicate/changed jobs, limits concurrency to one, and preserves
uncertain outcomes. On restart, known containers are removed before jobs become `recovered`;
those original jobs remain non-replayable. A new explicitly approved run is required.

These controls are defense in depth. Shared-kernel/runtime vulnerabilities, toolchain compromise,
test quality, side channels and operator mistakes remain risks. gVisor adds a syscall isolation
layer; ordinary Docker/Podman by itself is not the claimed security boundary. The live probes
below are necessary checks, not a comprehensive sandbox security certification.

Official references: [gVisor installation](https://gvisor.dev/docs/user_guide/install/),
[rootless modes and limitations](https://gvisor.dev/docs/user_guide/rootless/),
[Podman resource/filesystem options](https://docs.podman.io/en/latest/markdown/podman-run.1.html).
Use caller-configured user namespaces through rootless Podman. Do not substitute `runsc
--rootless` blindly: its documented cgroup and network limitations differ.

## Explicit host preparation (owner action)

1. Supply an existing disposable Linux VM or local Linux machine. No paid VM is required or
   provisioned by this project. Give the VM an outer resource cap (for example 2 GiB RAM) before
   running adversarial resource probes. Do not use a shared production host.
2. Install Podman and gVisor from their official instructions. Create an unprivileged account,
   configure `/etc/subuid` and `/etc/subgid`, and delegate `cpu`, `memory` and `pids` cgroup v2
   controllers. Verify `podman info --format=json` reports rootless mode and those controllers.
   Do not grant the account sudo, privileged mounts or Docker group access.
3. Check out this exact reviewed PR commit. Install the locked Python environment described in
   [Windows/local setup](local-owner-windows.md), using `.venv/bin/python` on Linux.
4. Select and inspect an official Python 3.12 slim image digest, then build the trusted tool image:

```sh
# Replace with the verified registry digest; no floating tag is supplied by this guide.
podman build --build-arg PYTHON_BASE=docker.io/library/python@sha256:REPLACE_WITH_VERIFIED_DIGEST \
  -f deploy/worker/Containerfile -t localhost/repopilot-worker:reviewed .
export REPOPILOT_WORKER_IMAGE="$(podman image inspect localhost/repopilot-worker:reviewed --format '{{.Id}}')"
```

The build installs pinned pytest/Ruff using the existing lock constraints. It installs no task
repository dependencies. Inspect/scan the image, retain its exact digest and record tool versions.

## Run the isolation acceptance harness

```sh
export REPOPILOT_LIVE_SANDBOX_IMAGE="$REPOPILOT_WORKER_IMAGE"
export REPOPILOT_SANDBOX_ACK=disposable-test-host
.venv/bin/python -m pytest tests/test_sandbox_live.py -v --junitxml=worker-live.xml
```

The six cases check benign execution/teardown, UID/filesystem/socket/secret/network boundaries,
disk exhaustion, bounded memory pressure, process pressure, CPU timeout and cancellation.
No candidate is ever executed on the controller. Missing prerequisites cause skips or errors;
they never trigger an ordinary container or host fallback. Inspect raw receipts and container
state when a check fails. Keep owner dispatch disabled until this host passes and is reviewed.

## Start the separate worker controller

Only after the host validation above, create a dedicated HMAC key file (32 random bytes), mode
0600, and an empty state directory mode 0700. Keep both outside Git and outside the image.
Share the key only with the trusted dispatcher, never with tested code or the browser.

```sh
export REPOPILOT_WORKER_STATE=/home/WORKER_USER/repopilot-state
export REPOPILOT_WORKER_KEY_FILE=/home/WORKER_USER/secrets/worker.key
.venv/bin/python -m uvicorn repopilot.worker_server:create_worker_app --factory \
  --host 127.0.0.1 --port 8012 --workers 1
curl --fail http://127.0.0.1:8012/health
```

Do not expose port 8012 publicly. A cross-machine controller needs an authenticated SSH tunnel
terminating at loopback; the existing transport intentionally rejects arbitrary remote URLs.
Health means the service started, not that isolation has been independently certified.

The standalone service implements the signed `/v1/execute` and `/v1/cancel` protocol. Production
owner dispatch is deliberately **not wired** to it yet. The next integration gate is to review
the actual host evidence, wire the existing WorkerDispatcher to this endpoint under the owner
execution route, and run the real model/App acceptance task. No receipts from mocked tests may
be used to open that gate. Until then, the local application supports planning and review only.

Troubleshooting: `sandbox_cgroup_or_rootless_unavailable` needs host delegation; image errors
need an explicitly built local digest; `sandbox_effective_configuration_rejected` means actual
mount/runtime/resource settings differ; `sandbox_cleanup_unconfirmed` requires operator cleanup
before restarting. Never disable a check, add privileged flags or widen host mounts to proceed.
