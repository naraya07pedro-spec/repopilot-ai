# Provider integration and model compatibility

V3 supports five explicit wire protocols behind the same validated Plan contract (including
complete file contents). These adapters are **contract-tested**, not live-model validated.
The deterministic fixture provider remains separate and unchanged. No model is selected
automatically; no provider fallback or cross-provider transfer exists.

| Provider | API contract | Model availability | Capability requirement |
| --- | --- | --- | --- |
| OpenAI | Chat Completions, strict JSON schema, store=false | GET /v1/models | Operator verifies Chat Completions JSON-schema support |
| Anthropic | Messages, output_config.format, end_turn | GET /v1/models with bounded pagination | JSON-schema output; no tools or thinking requested |
| Gemini | generateContent, responseJsonSchema | GET /v1beta/models with bounded pagination | JSON-schema output; reasoning usage is included when reported |
| Ollama | /api/chat, stream=false, JSON schema | /api/tags, already installed models | Local structured-output model; no downloads by RepoPilot |
| Local compatible | /v1/chat/completions | /v1/models | Exact supported OpenAI-compatible subset, including token usage |

Discovery checks the configured identifier; it does not prove context length, pricing or
structured-output support. The capability registry is an owner-maintained allowlist.
Unsupported responses, refusals, truncation, missing/invalid usage and unexpected tool calls
fail closed. Server-side Pydantic validation retains all length and shape constraints even
where the wire schema omits provider-incompatible length keywords.

## Configuration

Create a private JSON file outside Git and set REPOPILOT_MODEL_PROFILES_FILE to its path.
At most 20 profiles are accepted. This example uses a placeholder that must be replaced
with an **already installed** local model identifier; it is not a claimed available model:

```json
[
  {
    "id": "local-coder",
    "provider": "ollama",
    "model": "replace-with-installed-model",
    "structured_output": "json_schema",
    "context_tokens": 16384,
    "output_tokens": 1024,
    "context_bytes": 10000,
    "endpoint": "http://127.0.0.1:11434",
    "input_rate": 0,
    "output_rate": 0
  }
]
```

For local compatible servers set provider=compatible and endpoint=http://127.0.0.1:PORT/v1.
Only literal 127.0.0.1 or ::1 HTTP endpoints with explicit ports are accepted. No DNS names,
userinfo, query strings, redirects or arbitrary remote origins. The owner must control that
local service and verify it runs locally rather than forwarding to a paid/cloud model.
No cloud key is sent to local endpoints; the application HTTP client ignores proxy environment
variables. Local models consume real hardware resources; an 8 GB laptop is not assumed capable
of large coding models. RepoPilot never installs or pulls model weights.

For official providers omit endpoint; fixed official HTTPS origins are used. Select the exact
model identifier from that provider's API and verify its capabilities in official documentation.
Set positive conservative input_rate/output_rate values in USD per million tokens. Keep secrets
in OPENAI_API_KEY, ANTHROPIC_API_KEY or GEMINI_API_KEY on the backend only. Keys cannot be placed
inside profiles or submitted in the UI. The local file must be readable only by the owner/service
account; there is no browser secret storage or multi-user BYOK vault.

Paid generation additionally requires **all** of:
- REPOPILOT_ALLOW_PAID_MODELS=true (explicit server authorization).
- Positive REPOPILOT_DAILY_USD and REPOPILOT_RUN_USD.
- A configured credential, model and positive conservative pricing bounds.
- Per-run paid_approved=true plus a requested run limit no greater than the server limit.

The UI requires explicit consent naming the selected provider/model. Changing repository, issue,
model or budget clears consent. An uncertain request retains its idempotency key for a retry.
Local profiles work at zero API budget. Legacy single-model server configuration also requires
REPOPILOT_ALLOW_PAID_MODELS=true; use profiles for the model selector.

## Limits and evidence

Input is limited to 40 KB or the profile's smaller limit. A conservative admission estimate
uses UTF-8 bytes plus 4,096 protocol tokens; it must fit the configured context and output cap.
Output is capped at 4,096 tokens and 64 KB. Profiles set request_timeout_seconds from 1 to 120
(default 30), included in the approval binding. This is an HTTP I/O timeout, not proof of a total
wall-clock execution limit. A slow local runtime can explicitly use 120 without changing paid
provider defaults. Only explicit
429/502/503 responses get one retry, with a second budget reservation. Unknown transport outcomes
are not retried. Provider error bodies and credentials are never returned to the browser.

All providers share atomic daily reservations. A paid run must fit two worst-case reservations;
ambiguous/failed calls retain reservations. Usage is reported separately from conservative
reservations; estimated cost is not an invoice or a guarantee against incorrect operator pricing.
Anthropic prompt caching is not requested; unexpected cache accounting fails closed. Gemini
reported thought tokens count as output usage. Missing billing information is never invented.

Approval binds the exact snapshot/baseline, plan, profile, context/output/pricing limits, run
and daily budget, and a one-hour expiry. Changed configuration cannot silently reroute a queued
request. Private execution stays disabled; plan approval does not run code.

## Official protocol references

Reviewed 29 October 2026:
- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat)
  and [models](https://developers.openai.com/api/reference/resources/models/methods/list).
- [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
  and [model discovery](https://platform.claude.com/docs/en/api/models/list).
- [Gemini structured output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output)
  and [models](https://ai.google.dev/api/models).
- [Ollama chat](https://docs.ollama.com/api/chat) and [local model list](https://docs.ollama.com/api/tags).

No provider/model pair has a live success record in this environment. Official credentials,
paid-call authorization or an installed local model are still required for that release gate.
