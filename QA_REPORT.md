# PR #10 QA report

**Release verdict: NOT MERGE READY — real-model acceptance remains blocked by RAM.**
Independent local gates pass. Current remote CI results are the checks attached to
[PR #10](https://github.com/naraya07pedro-spec/repopilot-ai/pull/10); this report does not
preclaim a result for a future pushed commit.

| Check | Executed result |
| --- | --- |
| Ruff check / formatting | Passed |
| Strict mypy, win32 and linux platforms | Passed, 30 application modules |
| Backend `pytest --cov` | 300 passed, five environment skips, 93.81% coverage, 136.08 s |
| Skips | Four PostgreSQL cases not configured locally; one Windows symlink privilege case |
| TypeScript / component tests | Passed; 15 component tests |
| Public production build | Passed, Pages base path `/repopilot-ai` |
| Public setup browser checks | Six viewports: 360, 390, 768, 1366, 1440, 1920 px; reduced motion; no overflow/page errors/API or localhost requests |
| Local workspace browser checks | Two viewport journeys: clarification, runtime check, proposal, approval, actual patch download; explicitly synthetic model transport |
| Live public HTTPS | HTTP 200; desktop/mobile existing recording flows passed; private/API routes absent |
| Fresh Windows wheel install | New venv, PyPI runtime dependencies, no editable/source import, pip check passed |
| Installed console / assets / auth | Passed with cp1252 console; UI assets present; unauthenticated API rejected; missing runtime error verified |
| Installer cleanup | Own process tree stopped, test listener confirmed gone; no broader cleanup |
| Wheel integrity | 34 package files match source bytes; old experimental files rejected; clean wheel SHA in evidence |
| Fresh Linux install | New Ubuntu CI installed-package job verifies the same distribution/HTTP journey; consult current PR checks |
| Genuine model-through-app acceptance | NOT RUN: 896.43–1,003.54 MiB available vs 1,536 MiB start requirement |

The new browser suite supplements the existing browser suite; it does not replace sandbox
probes or real inference. Parsing Python is not execution. No model-generated Python ran,
no code was applied and no autonomous GitHub publication was enabled. No security bypass,
Windows restart, WSL/Hyper-V operation or change to OpenClaw was made.

The retained local logs, failed/rejected wheel, new source archive, clean wheel, fresh venv,
private launcher logs and sanitized installation receipts are under
`D:\Projects\repopilot-local\release-pr10-2026-11-01`. Launcher/session logs are deliberately
not committed or uploaded. [Sanitized evidence](evidence/pr10-release-readiness.json) records
hashes and the actual memory admission decision.

![Built public entry preview, not a deployment](docs/images/pr10-public-preview.png)

![Local workspace browser contract, explicitly synthetic transport](docs/images/pr10-workspace-contract.png)

Remaining owner action: make sufficient free RAM available while keeping OpenClaw/Codex
running, then repeat only the guarded real-model acceptance. Keep the 512 MiB running floor,
CPU-only runtime settings and exact-proposal review. Do not merge based only on these tests.
