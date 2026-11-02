# Recruiter walkthrough — proposal edition release candidate

Start with [PR #10](https://github.com/naraya07pedro-spec/repopilot-ai/pull/10), the current
[capability matrix](capabilities.md), and its CI checks. The public Pages URL still hosts the
previous fixture viewer. The candidate can be distributed as an explicitly labeled preview
independently of personal-PC inference; stable acceptance remains unverified.
The new product entry is tested in a static preview; it is not claimed deployed yet.
Download the exact tested [preview artifacts](preview-release.md) from its successful CI run.

## One-minute product tour

1. **Try RepoPilot** explains the Python installation and the user-owned model runtime.
   The site never connects to the developer's PC or the visitor's localhost.
2. **Real model recording** is labeled recording, not live. Until the new acceptance succeeds,
   it shows the earlier CPU Qwen model-only proposal, stopped for approval. Its exact provenance
   and limitation remain visible.
3. **Separate engine evidence** retains the original deterministic fixture runs: baseline,
   scoped diff, checks, rejection path and actual Issue #1 → PR #2. Those results do not prove
   a real-model isolated agent workflow.
4. **Capability matrix** distinguishes implemented proposal orchestration from disabled
   sandbox execution and autonomous publication. No subscription or API key is mandatory.

## Reproduce the usable path

Follow [self-hosted setup](self-hosted.md) from a fresh environment. Start an existing compatible
llama.cpp or Ollama runtime, then launch the installed `repopilot local` command against a
committed Python repository. For the included example, clone the release branch into a new
folder and choose its `examples/mean` directory as `--repo`.

Open the private session link printed in your terminal. Check runtime availability, select
`app.py` and request: “Replace // with / in app.py. mean([1, 2]) must return 1.5. Preserve the
empty-list ValueError and all other lines. Return one complete app.py edit.”

Inspect the stored stages, actual model usage, diff and risks. Approve the exact proposal,
then download the patch. Reopen history and verify the exported checkpoint. Nothing is applied,
executed or published. Changing the source invalidates approval/export. Small models can
produce incorrect proposals even when syntax validation passes.

## Evidence labels

- A fresh installed-wheel HTTP smoke checks packaged assets, authentication, the launcher
  and disabled execution/publication without invoking any model.
- Browser integration uses an explicitly synthetic transport, labeled in the UI/test names.
  It verifies forms, clarification, diff review, approval and real patch download.
- The real local-model acceptance must run the installed application with the guarded CPU
  runtime and show proposal → approval → patch download. It is the outstanding gate when
  available RAM is insufficient. No failed/blocked attempt is replaced with fixture output.

Skills demonstrated: Python/FastAPI, structured provider adapters, SQL checkpoints and
compare-and-swap transitions, cancellation/recovery, exact approval binding, packaging,
Next.js/TypeScript, browser verification and honest security boundaries. Do not turn these
results into claims about customers, production scale, frontier model quality or completed
secure autonomous Issue-to-PR execution.
