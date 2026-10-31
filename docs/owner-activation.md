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

## One provider: OpenAI, with paid generation still denied

1. Sign into the official [API dashboard](https://platform.openai.com/). Select the intended API
   project. Open **API keys → Create new secret key** and store it in the backend's protected
   environment as `OPENAI_API_KEY`. A ChatGPT subscription does not establish API billing access.
   Do not add payment, buy credits, or make a generation call as part of this task.
2. Select an identifier returned by that project's model discovery and confirm **Chat Completions
   plus strict JSON-schema output** in its official model documentation. There is no preselected
   marketing model name or automatic fallback.
3. Create a private UTF-8 JSON profile outside Git using the template below. Replace every numeric
   zero with a verified capability bound or conservative current per-million-token price before
   loading it. Template zeros deliberately do not form a valid usable paid profile.

```json
[
  {
    "id": "owner-openai",
    "provider": "openai",
    "model": "REPLACE_WITH_VERIFIED_MODEL_ID",
    "structured_output": "json_schema",
    "context_tokens": 0,
    "output_tokens": 0,
    "context_bytes": 0,
    "input_rate": 0,
    "output_rate": 0
  }
]
```

4. Set `REPOPILOT_MODEL_PROFILES_FILE` to that private file. Keep
   `REPOPILOT_ALLOW_PAID_MODELS=false`, `REPOPILOT_RUN_USD=0`, `REPOPILOT_DAILY_USD=0` until the
   owner explicitly approves spending. The [profile limits](providers.md) define accepted ranges.
   `python -m repopilot.doctor` checks presence without printing values or making API calls.
5. Once spending is separately authorized, set the exact approved positive run/daily ceilings and
   `REPOPILOT_ALLOW_PAID_MODELS=true` server-side. Restart the backend. The owner must additionally
   select this profile and approve paid calls for each run; the per-run limit cannot exceed the
   server ceiling. Configured pricing is a reservation estimate, not a guaranteed provider invoice.
6. First check model availability, then perform one explicitly approved planning call. Discovery
   is not generation evidence. Code testing/publication remains blocked until worker validation
   and the reviewed dispatcher binding are complete.

[Official server-side authentication](https://developers.openai.com/api/reference/overview) ·
[structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat) ·
[provider contract and bounds](providers.md).

For zero API spend, an already installed suitable local model is an alternative described in
providers.md. No local model/hardware is assumed available and RepoPilot downloads no weights.

## Real acceptance still blocked

After the [runtime prerequisite](runtime-options.md) changes: validate the separate worker,
review the gated owner dispatch integration, configure a private transport key and loopback/tunnel,
then read a scoped real Issue, generate and approve the exact candidate/model/budget, run isolated
tests, review receipts and approve a draft PR. Reconcile uncertain writes and confirm no duplicate
commits/PRs after retry/restart. That acceptance has not occurred; Issue #1 → PR #2 is deterministic.
