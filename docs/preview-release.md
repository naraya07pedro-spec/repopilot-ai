# RepoPilot AI proposal preview

This is a usable implementation preview, not a verified general-purpose coding agent.
Installation, packaged UI/API, authentication, persistent orchestration, proposal validation,
exact approval and patch export have automated coverage. Browser model transports are
explicitly synthetic. The complete installed-app → genuine local model → approved patch
acceptance is **unverified**, currently blocked by the evaluation PC's available RAM.
Earlier real CPU Qwen model-only evidence does not replace that acceptance.

You can evaluate the UI and connect your own existing model. Model quality and successful
generation are not guaranteed. No weights, runtime, paid service or sandbox is installed.
Generated code is never executed, applied or autonomously published.

## Durable experimental prerelease

Download [v0.2.0-preview.1](https://github.com/naraya07pedro-spec/repopilot-ai/releases/tag/v0.2.0-preview.1).
The versioned ZIP and its SHA-256 sidecar do not depend on expiring Actions artifacts.
It pins verified checkpoint 218df1a3b934e4dc1be3ab1410bc313296ba93fd.
The separate static preview host is https://naraya07pedro-spec.github.io/repopilot-ai-preview/.
This host has no model/backend and does not replace the default website.

## CI candidate artifacts

Open PR #10's **Verify** workflow for the desired commit in
[GitHub Actions](https://github.com/naraya07pedro-spec/repopilot-ai/actions/workflows/verify.yml).
Wait for all five jobs to pass. Download **repopilot-ai-preview-COMMIT_SHA** from that run's
Artifacts section and extract it into a new folder. GitHub may require sign-in to download
Actions artifacts; these preview downloads expire after 30 days. No PyPI release or public
GitHub Release is claimed. Use the source-install alternative below if the artifact expired.

The bundle contains a universal Python wheel, audited dependency constraints, this guide,
MIT license, committed source archive, `preview.json` provenance and `SHA256SUMS`.
Check that `preview.json`'s `source_commit` matches the successful workflow's commit.
SHA-256 checks detect changed bytes; authenticity still depends on the trusted repository/run.
The bundle needs internet access to install dependencies; it is **not** an offline installer.

From the extracted bundle, verify every checksum before installing:

```powershell
# Windows PowerShell; run from the extracted bundle directory.
Get-Content .\SHA256SUMS | ForEach-Object {
    $expected, $name = $_ -split '  ', 2
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $name).Hash.ToLowerInvariant() -ne $expected) {
        throw "Checksum mismatch: $name"
    }
}
```

```sh
# Linux; run from the extracted bundle directory.
sha256sum --check SHA256SUMS
```

Requires Python **3.12** (the CI-tested version), Git and an existing committed Python
repository. Choose a new virtual environment directory:

```powershell
python -m venv .venv-repopilot
.\.venv-repopilot\Scripts\python.exe -m pip install -c requirements.lock .\repopilot_ai-0.2.0-py3-none-any.whl
.\.venv-repopilot\Scripts\repopilot.exe local --repo "D:\path\to\committed-repository" --model YOUR_INSTALLED_MODEL
```

```sh
python3 -m venv .venv-repopilot
.venv-repopilot/bin/python -m pip install -c requirements.lock ./repopilot_ai-0.2.0-py3-none-any.whl
.venv-repopilot/bin/repopilot local --repo /path/to/committed-repository --model YOUR_INSTALLED_MODEL
```

The default provider is native Ollama at `http://127.0.0.1:11434`. For an existing
llama.cpp/schema-compatible server, append `--provider compatible --endpoint
http://127.0.0.1:8080/v1` and use its served model alias. There is no model download.

Open the private session URL printed by the launcher on the **same machine**. Keep it
private. Select Python files, check runtime availability, enter a focused task, review
the actual proposal, approve it, then download the patch. Runtime discovery does not
prove generation quality. Without a runtime, you can inspect onboarding/files/history;
runtime checks and generation report an error instead of returning fake AI output.

The source archive has no `.git` history: it is for source inspection/development, not
a committed task repository. Use the clone below for the included committed starter.
Stop the launcher with Ctrl+C; it does not stop your model runtime or other applications.

## Source installation and included starter

Follow [self-hosted setup](https://github.com/naraya07pedro-spec/repopilot-ai/blob/codex/usable-agent-release/docs/self-hosted.md).
Its clone goes into a new folder and refuses to overwrite an existing one. Install with
`-c requirements.lock .` from that clone, then select `examples/mean` as the repository.
For an exact reproduction, run `git checkout --detach COMMIT_SHA` in the **new clone**
before installation, using the verified workflow commit. The branch may advance.

## Public preview and release gates

The separately downloadable **public-preview-pages-COMMIT_SHA** is the tested static
frontend built for `/repopilot-ai`. It has no model/API backend, credentials or localhost
connection. It labels the earlier model recording and separate fixture evidence explicitly.
It can be published as a **preview**, with these limitations visible, independently of
personal-PC inference. Downloading an artifact does not deploy it. The existing Pages
workflow deploys only from `main`; PR #10 is not automatically merged or deployed.

A stable release and full genuine-model acceptance remain separate gates. Neither green
CI nor publication of a preview proves local-model success. Secure isolated tests and
autonomous GitHub publication remain disabled advanced capabilities.
