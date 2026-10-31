# Minimum-cost activation checklist

Current result: the public recording viewer is verified; the private real-agent acceptance is
incomplete. No paid infrastructure is necessary for local planning. Nothing below authorizes
paid calls, automatic merging, unrelated repositories or bypassing the closed execution gate.

## 1. Start the owner workspace without external credentials

Follow [Windows commands](local-owner-windows.md). Run `python -m repopilot.doctor`, start the
API with `python -m uvicorn repopilot.api:create_app --factory --host 127.0.0.1 --port 8000`,
and run `npm.cmd run start` in frontend with the matching origin/backend environment. Sign in
at http://127.0.0.1:3000/owner. Missing connections and disabled execution are expected.
SQLite is adequate for this single-owner local setup; no cloud PostgreSQL purchase is needed.

## 2. Configure GitHub App access when available

In the **naraya07pedro-spec** GitHub account:

1. Open **Settings → Developer settings → GitHub Apps → New GitHub App**.
2. Set a unique name and this repository as Homepage URL. Disable webhook Active; this app polls.
3. Choose **Only on this account**. Grant Metadata/Contents/Issues read access for planning.
4. Create the App. Open **Credentials → Key pairs → New key** and store the downloaded PEM
   outside Git. Record the App ID in the server configuration.
5. Choose **Install App**, select your account, then **Only select repositories → repopilot-ai**.
   Record the installation ID and configure the key path plus repository/source-root allowlists.
6. In RepoPilot, click **Validate approved repositories**. Do not substitute another fork/account.

Before a later approved publication run, the installation must additionally have Contents write
and Pull requests write permissions. The application still requests read-only repository tokens
for inspection and a separate write token for explicitly approved publication.

Follow [GitHub registration](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app)
and [key management](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps).
No key, token or private repository text belongs in chat or public recordings.

## 3. Configure exactly one model to begin

For zero API spend, use an already installed, structured-output-capable Ollama/local model on
suitable hardware and the [local profile example](providers.md). An 8 GB Windows laptop is not
assumed capable of running large coding models. RepoPilot does not download models automatically.

Alternatively configure one official provider credential server-side. First approve an explicit
run/daily spending ceiling and verify current model capability/pricing. Keep paid opt-in false
until that approval exists. ChatGPT subscription access is not API spending authorization.
Select provider/model explicitly in the owner UI and click **Check model availability**.
Discovery is not a successful model-generation test.

## 4. Validate the worker before activation

Supply a dedicated disposable Linux VM/host and follow [Linux worker setup](linux-worker.md).
Build the reviewed tooling image, record its digest, and run all six live isolation probes.
Retain raw output, runtime/kernel/tool versions and cleanup evidence. Fix actual failures;
do not add privileged flags or switch to ordinary Docker/host execution.

After an engineering review of those results, wire the existing WorkerDispatcher into the owner
execution route with a private HMAC key and authenticated loopback/tunnel endpoint. This final
binding is intentionally not active in this release. Passing controller mocks cannot enable it.

## 5. Run the real acceptance task

Within the authorized repository, use a scoped Issue targeting fixtures/bug and a fresh request
identity. Inspect the actual model-generated plan/diff and approve its exact baseline, source
scope, provider and budget. After verified runtime activation, dispatch, inspect actual command
receipts, preview publication, and separately approve a draft PR. Reconcile an uncertain response
before any retry. Confirm a repeated request creates no duplicate branch/commit/PR. Never merge
automatically. Save the real run/commit/Issue/PR identities and browser evidence privately.

Until this passes, Issue #1 → draft PR #2 remains **deterministic fixture evidence only**.
Private cloud deployment and Netlify publication remain deferred; neither is needed for this
local acceptance path. Production would additionally need approved hosting, HTTPS, private
PostgreSQL, monitored backups/recovery and an independently reviewed worker deployment.
