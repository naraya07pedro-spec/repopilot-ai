# PR #10 implementation report

The release candidate reuses the verified Windows provider/planning/approval work at
8c638c1. Local tasks use the existing engineering_runs persistence and approval binding;
the proposal loop reads selected Python source, invokes configured adapters, validates as
data, permits bounded correction/fallback and exports only an approved, unchanged patch.
The local UI is bundled with the Python package. No new framework, model or sandbox is needed.

The public entry remains the existing Next.js App Router static export. The private Next
console is preserved. The new local workspace uses lightweight bundled HTML/CSS/JavaScript,
loopback FastAPI and an ephemeral session token. No Node runtime is needed by installed users.
The visual system uses the existing dark palette, restrained green accent, system/monospace
fonts and CSS transitions. There is no generated imagery, cinematic media, new animation
dependency or shared transform/scroll engine. Mobile reflows the sidebar/forms and preserves
all actions; reduced motion disables transitions. See screenshots and QA evidence.

The public journey is promise → local setup → explicitly recorded model evidence → separate
deterministic fixture evidence → capability boundary. Its stateful setup selector provides
Windows/Linux commands and runtime instructions. It never fetches a localhost API or asks
for credentials. Existing fixture recordings retain their provenance and tests.

This follow-up fixes Linux typing of the Windows lock module, missing evidence in the Docker
frontend context, legacy Windows console output, configuration errors, reparse-point guards,
clarification form state and installer process-tree cleanup. Fresh wheel verification checks
all 34 package source/assets against the checkout. A contaminated wheel from an older ignored
build cache was rejected; the new wheel came from a fresh source archive. No cache/source
directory was destructively cleaned. All retained test/build artifacts are on D:.

Installation and launch commands are in [self-hosted setup](docs/self-hosted.md). The candidate
uses `git+https://github.com/naraya07pedro-spec/repopilot-ai.git@codex/usable-agent-release`.
The fresh installed console entry point and HTTP workspace passed on Windows. CI now tests
fresh installed distributions on both Ubuntu and Windows. Backend/frontend/container CI gates
remain present. The release browser tests are explicitly synthetic transport contracts.

The previous public HTTPS fixture site is still deployed. Its two desktop/mobile browser
flows passed. The new public entry is built and browser-tested locally; it is not claimed live.
Deployment remains behind PR review and the outstanding real-model acceptance.

The only remaining product acceptance is installed application → genuine local CPU model →
proposal → exact approval → downloaded patch. Available RAM failed the 1,536 MiB start guard;
no model process was started and no guard was weakened. No WSL/Hyper-V/admin operation or
OpenClaw interruption occurred. Secure code execution and autonomous GitHub publication
remain disabled advanced features and are not prerequisites for this proposal edition.
