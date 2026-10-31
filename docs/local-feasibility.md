# Local-first feasibility audit — 31 October 2026

The target is this existing Windows laptop: local FastAPI + production Next.js, local inference,
SQLite, GitHub only for authorized repository operations, and a verified sandbox evaluated in
WSL2. No paid model API, rented server or cloud deployment is required or authorized.
PR #9 is the independently reviewed application; PR #8 preserves the failed runtime experiment.

## Measured machine, not the approximate 8 GB estimate

| Check | Actual read-only result |
| --- | --- |
| Installed RAM | One 4,294,967,296-byte module: **4 GB installed** |
| Windows-visible RAM | 4,126,380,032 bytes, about 3.84 GiB |
| Available RAM | About 485–549 MiB during two samples; transient, not a capacity guarantee |
| CPU | i3-8130U, two physical cores / four logical processors |
| GPU | Intel UHD 620; no verified dedicated inference accelerator; plan CPU-only |
| Disk | About 33.4 GiB free on C: |
| Virtualization | Firmware virtualization and SLAT true; hypervisor not present |
| Windows | Windows 11 Home Single Language, build 26300 |
| WSL | wsl.exe launcher exists, but --status exits 50: WSL is not installed |
| Windows features | VirtualMachinePlatform and WSL both disabled (InstallState 2) |
| Other runtimes | No ollama, podman or docker executable found; no WSL service |
| Current privileges | Standard user, not an elevated Windows administrator |

Reproduce without installation or network calls:
`./scripts/audit-local-windows.ps1`. The audit omits names/serial numbers, credentials and
process inventories. [Sanitized measured record](../evidence/local-hardware-audit-2026-10-31.json).
No feature, runtime, model, driver, pagefile or host setting was changed during the audit.

## Smallest model candidates and memory decision

| Model | Official quantized artifact | Appropriate next evaluation |
| --- | --- | --- |
| qwen2.5-coder:0.5b | 398 MB, Q4_K_M | Smallest smoke-test candidate; limited coding capability must be measured |
| qwen2.5-coder:1.5b | 986 MB, Q4_K_M | Smallest practical coding **candidate to test** for this one-file issue profile; not yet validated |

Artifact sizes are download/weight sizes, **not total RAM**. Context/KV cache, runner buffers,
model runtime, Windows, browser, API, Next.js and WSL/worker require additional memory. No model
has run here, so generation latency, schema reliability, peak working set and coding quality are
unknown. No model can honestly be certified practical on this machine from a catalog size alone.
The existing 30-second provider timeout and strict response/budget validation remain enforced.

With less than 550 MiB available, even the 398 MB weights leave no measured runtime/worker
headroom. **Concurrent Windows + model + API/frontend + WSL sandbox is not established and is
not a sensible installation target under the measured load.** No model/runtime download was made.
An actual 8 GB machine could merit a 1.5B trial, but that is not the installed capacity observed.
No hardware upgrade or other purchase is authorized by this recommendation.

Sequential phases may lower peak memory: generate a bounded candidate, unload the model, retain
the plan for approval, then start verification. The existing Ollama adapter already sends
keep_alive=0 and explicit num_ctx/num_predict. Contract tests assert these and test the shipped
profiles at zero budget. Sequential operation still needs measured headroom and a passing sandbox;
it is a proposed evaluation strategy, not completed local-agent evidence.

## Local model configuration prepared without downloads

`deploy/local-models.example.json` contains two literal-loopback, zero-price profiles. The 0.5B
profile admits at most 3,584 serialized request bytes / 512 output tokens; the 1.5B profile admits
3,072 bytes / 1,024 output tokens. Both request an 8,192-token context. Fixture requests fit the
existing conservative admission rule; larger issues fail rather than silently exceeding it.
The file does not install a model or assert its availability.

When memory is genuinely available and Ollama is installed, configure its **own process** before
startup with OLLAMA_NO_CLOUD=1, OLLAMA_HOST=127.0.0.1:11434, OLLAMA_NUM_PARALLEL=1 and
OLLAMA_MAX_LOADED_MODELS=1. Restart an existing Ollama process for these settings to take effect.
Check its local/cloud-disabled status and /api/tags before using an already installed model.
Do not select a cloud model, sign into a model service, expose the port, or download larger weights
as a fallback. Native Ollama installation alone needs at least 4 GB of disk per its current docs;
no installer was started here. It normally requires no Windows administrator access.

The backend keeps REPOPILOT_ALLOW_PAID_MODELS=false and both USD limits at 0; no OpenAI,
Anthropic or Gemini key is needed. Historical cloud adapters stay contract-tested, not required.
All new local-owner tests use explicitly synthetic HTTP responses, not invented local inference.

## WSL2 evaluation boundary

WSL2 is unavailable until Windows administrator setup/reboot. It is a Linux evaluation host,
not the hostile-code sandbox. Do not enable owner execution merely because Ubuntu boots.
Before any adversarial probe, a disposable dedicated distro must be separated from Windows
credentials/files: disable drive automount/fstab processing and Windows interop in its wsl.conf,
keep source under its Linux filesystem, use an unprivileged account and subordinate IDs, and
verify cgroup v2 CPU/memory/pids delegation and user/network namespace behavior. Do not mount a
Docker socket or bind Windows directories into the guest. WSL memory caps must leave Windows
headroom; no cap can make a 4 GB machine behave as an 8 GB machine.

Do not copy the Windows checkout into a broadly shared /mnt/c worker workspace. Transfer only
approved bounded fixture bytes after the controller/guest boundary is reviewed. Do not expose
Ollama with 0.0.0.0 as a cross-WSL workaround; local inference can remain on the Windows control
plane, and a future worker uses a separately authenticated transport.

The released gVisor/systemd and cgroupfs failures in PR #8 remain relevant in WSL. No WSL
kernel, cgroup delegation or compatible sandbox has been tested here. Inspect these prerequisites
read-only after installation; **do not rerun the known incompatible configuration unchanged**.
Only a reviewed compatible runtime may run the six preserved live probes and actual resource/
network/filesystem/cancellation/recovery checks. The production dispatch/publication gate remains
closed until those pass. No speculative WSL/microVM worker code was added.

## Only owner-only manual actions

1. **Windows administrator:** if proceeding with WSL prerequisites, open Start → PowerShell →
   Run as administrator, run `wsl --install --no-distribution`, approve Windows elevation and
   reboot if requested. This avoids a default Ubuntu download. After reboot the agent can
   re-audit `wsl --status` and memory before deciding whether a distro/model download is feasible.
   No distro or model installation is recommended under the currently measured memory load.
2. **GitHub account authorization:** follow the exact App creation/selected-repository/key steps
   in [owner activation](owner-activation.md). Keep the private key outside Git/chat. Read-only
   issue inspection comes first; approve Contents/Pull requests write only for the later draft-PR
   acceptance. No model account, API billing, server rental or hosting authorization is needed.

All other work remains agent-executable once those prerequisites and sufficient headroom exist.
Do not request provider secrets or a rented worker. An actual Issue → local model → verified
isolated tests → draft PR run has **not** succeeded.

## Primary sources

- [Ollama 0.5B model](https://ollama.com/library/qwen2.5-coder:0.5b) and
  [1.5B model](https://ollama.com/library/qwen2.5-coder:1.5b).
- [Windows requirements](https://docs.ollama.com/windows),
  [cloud-disable/concurrency/context controls](https://docs.ollama.com/faq),
  [local chat/keep_alive API](https://docs.ollama.com/api/chat).
- [WSL admin installation](https://learn.microsoft.com/en-us/windows/wsl/install),
  [no-distribution option](https://learn.microsoft.com/en-us/windows/wsl/basic-commands),
  [WSL configuration and Windows interop](https://learn.microsoft.com/en-us/windows/wsl/wsl-config).
