# Exact owner setup and activation boundaries

The portfolio release supports authenticated planning/review. Code execution and private PR
publication are disabled. Configuration below does not open that gate or authorize spending.
Do not paste credentials in chat, commit them or enter them in the public demo.

## GitHub App: configure read-only planning first

1. Sign into **naraya07pedro-spec**. Open profile picture → **Settings → Developer settings →
   GitHub Apps → New GitHub App**. Use a unique name and the RepoPilot repository as Homepage URL.
2. Turn **Webhook Active** off; this integration polls. Choose **Only on this account**.
3. Under Repository permissions, grant **Contents: Read-only**, **Issues: Read-only** and the
   automatically required **Metadata: Read-only**. Create the App.
4. Record its **App ID**. Generate a private key from the App settings, and save the PEM outside
   Git with access restricted to the backend owner account.
5. Choose **Install App → your account → Only select repositories → repopilot-ai**. Record the
   installation ID from the installation settings URL. Do not install the unrelated fork.
6. In the private backend environment configure:

```powershell
$env:GITHUB_APP_ID = 'YOUR_APP_ID'
$env:GITHUB_INSTALLATION_ID = 'YOUR_INSTALLATION_ID'
$env:GITHUB_APP_PRIVATE_KEY_FILE = 'C:\private\repopilot\app.pem'
$env:REPOPILOT_REPOSITORIES = 'naraya07pedro-spec/repopilot-ai'
$env:REPOPILOT_SOURCE_ROOTS = '{"naraya07pedro-spec/repopilot-ai":"fixtures/bug"}'
```

7. Follow [Windows startup](local-owner-windows.md), sign into `/owner`, and choose **Validate
   approved repositories**. Retain the actual success/error; configuration presence is not a
   live installation validation.
8. Only after isolated execution is verified and a publication test is separately approved,
   change **Contents** and **Pull requests** to **Read and write** and approve the installation's
   new permissions. Inspection still uses read-only tokens; publication requires explicit approval.

[Official App registration](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app).

## Local model only: no API keys or billing

The current mandate is **existing Windows laptop, zero paid API, zero rented server**.
The hardware audit found 4 GB installed RAM and no Ollama/WSL runtime. Read
[the measured feasibility result](local-feasibility.md) before any download. No model installer
or model pull was performed. No cloud API key is required, and paid generation stays denied.

The prepared `deploy/local-models.example.json` profiles select only the local Ollama endpoint
at http://127.0.0.1:11434 with zero input/output prices. They are candidate configurations, not
proof that model weights are present or that generation works. The 0.5B model is a smoke-test
candidate; the 1.5B model needs an actual quality/memory/latency evaluation before being called
practical. The measured laptop cannot currently demonstrate the full concurrent workload.

After sufficient memory headroom and an existing local runtime are verified, the agent can set
OLLAMA_NO_CLOUD=1, loopback-only OLLAMA_HOST, one parallel request and one loaded model in the
Ollama process. No cloud model, proxy/tunnel or external fallback is permitted. The adapter
already unloads the model after each request with keep_alive=0; contract tests verify this.

For the backend, use the [local environment example](../deploy/local-owner.env.example):

```powershell
$env:REPOPILOT_MODEL_PROFILES_FILE = (Resolve-Path deploy/local-models.example.json).Path
$env:REPOPILOT_ALLOW_PAID_MODELS = 'false'
$env:REPOPILOT_DAILY_USD = '0'
$env:REPOPILOT_RUN_USD = '0'
```

Follow [Windows startup](local-owner-windows.md). No model API credential or PostgreSQL service
is needed for local SQLite. `python -m repopilot.doctor` prints configuration presence only;
model discovery and successful schema-validated generation must be measured separately.
An unavailable endpoint remains an error. A synthetic response in CI is not local inference.

The only current Windows admin action and exact GitHub authorization steps are documented in
[local feasibility](local-feasibility.md#only-owner-only-manual-actions) and above. WSL2 alone
must not open execution. No cloud/paid activation instructions apply to this target.

## Real acceptance still blocked

After the [runtime prerequisite](runtime-options.md) changes: validate the separate worker,
review the gated owner dispatch integration, configure a private transport key and loopback/tunnel,
then read a scoped real Issue, generate and approve the exact candidate/model/budget, run isolated
tests, review receipts and approve a draft PR. Reconcile uncertain writes and confirm no duplicate
commits/PRs after retry/restart. That acceptance has not occurred; Issue #1 → PR #2 is deterministic.
