# Live sandbox CI diagnosis — 30 October 2026

**BLOCKED: isolation is not verified; PR #8 is not ready to merge.** The six tests are mandatory
and still fail. Owner execution and private publication remain disabled. No security assertion,
resource limit or runtime boundary has been removed to make CI pass.

## Reproduced environment and command

Implementation commit: `0c3ae880dea735f2cd083a3170efd40d9217f5e5`.
[Full CI](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/41090628500) ·
[Sandbox job and raw logs](https://github.com/naraya07pedro-spec/repopilot-ai/actions/runs/41090628500/job/124183254613).

- GitHub-hosted Ubuntu 24.04 image `20261025.353.1`, kernel `7.0.0-1017-azure`.
- Python 3.12.15, pytest 9.0.3, rootless Podman 4.9.3.
- gVisor `release-20261026.0`, OCI spec 1.2.1.
- Podman reports cgroup v2, systemd manager, and delegated CPU/memory/pids controllers.
- `REPOPILOT_SANDBOX_ACK=disposable-test-host`, with the locally built image's exact SHA-256 ID.
- Command: `python -m pytest tests/test_sandbox_live.py -v --junitxml=evidence/sandbox-live.xml`.

## Verified application defects corrected

1. `6857df3`: normalize Podman's exact bare 64-hex image ID to its SHA-256 representation.
   Mutable image tags remain forbidden.
2. `ea86ad0`: Podman 4.9.3 rejects `uid=65532` in a tmpfs mount (create exits 125). Use supported
   bounded sticky tmpfs; UID 65532 creates a private 0700 candidate directory. The live boundary
   test additionally checks that directory's ownership and mode.
3. `0c3ae88`: Podman inspection returns `/usr/local/bin/runsc`, not just `runsc`. Accept the
   exact configured absolute runtime path or existing alias, and reject other paths/runtimes.

Diagnostic commits `5b00c77` and `aac5a21` expose bounded/redacted stderr and selected inspection
fields. They never dump environment values or host mount paths. Live assertion messages retain
the already bounded command output. These corrections passed local controller regression tests.

## Remaining root cause: released gVisor systemd integration

Container creation and pre-start inspection now succeed. `podman start --attach --interactive`
then exits **125** with:

```text
creating container: systemd error: Interactive authentication required.
```

This matches [gVisor issue #11543](https://github.com/google/gvisor/issues/11543).
The [release source](https://github.com/google/gvisor/blob/release-20261026.0/runsc/cgroup/systemd.go)
opens the system systemd connection. In rootless Podman's caller-created user namespace,
namespace UID 0 does not authorize system-wide transient units. The failure occurs before
the candidate Python process starts. It is a runtime/host integration incompatibility, not
evidence that GitHub Actions universally lacks user namespaces or cgroup v2.

[Upstream fix #13853](https://github.com/google/gvisor/pull/13853) adds per-user systemd support
and checks requested controller availability. It was independently checked through GitHub's API
on 30 October 2026: **open, unmerged**. We did not install an unreviewed runtime fork, grant
system-wide polkit permissions, switch to rootful execution, or use `--ignore-cgroups`.
The latter would disable the very limits these tests must verify.

## Six live outcomes

| Probe | Actual result | What remains unverified |
| --- | --- | --- |
| Benign pytest/lint/format and teardown | Failed; command exit 125 | Successful guest execution and teardown |
| UID/filesystem/secrets/network boundary | Failed; command exit 125 | Guest identity, filesystem and network enforcement |
| Disk limit | Failed; command exit 125 | Actual ENOSPC/EDQUOT enforcement |
| Memory limit | Failed; command exit 125 | OOM/MemoryError under the memory cap |
| Process limit | Failed; command exit 125 | Rejection of excess guest processes |
| CPU deadline and cancellation | Failed at startup; cancellation phase not reached | Timeout, running-process cancellation and cleanup |

Harness exit: **1; 6 failed, 0 skipped**. The failure was not misclassified as resource exhaustion.
The driver's finally block confirmed removal of each named container object before returning
failed receipts. This is not proof of teardown or recovery of a running sandbox. Crash recovery
and replay remain controller-tested with synthetic runtime outputs, not live crash evidence.

Other jobs passed: 275 backend tests (six live cases skipped only in that separate job),
94.03% statement coverage (2,046/2,176), PostgreSQL, Ruff/format, mypy, secret-pattern scan,
Python dependency audit, 13 frontend component tests, six Chromium cases, TypeScript,
private/public builds, npm audit and container HTTP/tooling smoke. Full workflow result: **failure**.

## Dedicated Linux reproduction and future validation

A new host alone does not fix this released gVisor/systemd bug. Use an existing disposable Linux
VM with an outer resource cap and no model/App secrets; do not purchase or provision one for this
task. Follow [worker host preparation](linux-worker.md) for subordinate IDs and cgroup delegation.
Run as the unprivileged worker account, never via `sudo podman` or a privileged container.

```sh
git clone --branch feat/v3-providers https://github.com/naraya07pedro-spec/repopilot-ai.git
cd repopilot-ai
git switch --detach 0c3ae880dea735f2cd083a3170efd40d9217f5e5
python3.12 -m venv .venv
.venv/bin/python -m pip install -c requirements.lock -e '.[dev]'
id
uname -r
runsc --version
podman version
podman info --format=json
systemctl --user show --property=ControlGroup
podman pull docker.io/library/python:3.12-slim
base=$(podman image inspect docker.io/library/python:3.12-slim --format '{{index .RepoDigests 0}}')
podman build --build-arg PYTHON_BASE="$base" -f deploy/worker/Containerfile -t localhost/repopilot-worker:probe .
export REPOPILOT_LIVE_SANDBOX_IMAGE="$(podman image inspect localhost/repopilot-worker:probe --format '{{.Id}}')"
export REPOPILOT_SANDBOX_ACK=disposable-test-host
.venv/bin/python -m pytest tests/test_sandbox_live.py -v --junitxml=worker-live.xml
podman ps -a --filter name=rp- --format '{{.Names}} {{.Status}}'
```

Keep the pytest exit code/JUnit and complete output even when it fails. The final container query
must be empty; do not remove leaked objects before capturing the failure evidence. Record image
digests, runtime/kernel versions and host delegation. This reproduces a failure on the known
runtime combination; it is not a promise of a passing host configuration.

Next engineering action: re-evaluate a reviewed gVisor release containing compatible user-systemd
support, or an independently reviewed rootless delegated-cgroup configuration. Repeat all six
probes with unchanged security requirements, then run the full CI suite. Do not blindly install
an upstream PR or change cgroup/network flags. Only after real isolation evidence passes review
may the owner dispatcher binding and real-model/GitHub App acceptance proceed.
