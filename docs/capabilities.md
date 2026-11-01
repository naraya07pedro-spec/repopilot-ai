# Capability matrix — proposal edition 0.2

The release boundary is **task → genuine model → unexecuted proposal → human review → patch**.
It is a bounded proposal agent, not a claim of unrestricted autonomous software engineering.

| Capability | Implementation / verification |
| --- | --- |
| Local task intake | `LocalAgent.create_task`; selected-source consent and idempotency fingerprint persisted in the existing engineering_runs table |
| Clarification | Missing source selection produces needs_clarification without contacting a model; owner supplies paths to continue |
| Repository inspection | Read-only committed Git revision + selected UTF-8 Python text; hidden paths, symlinks, junctions and traversal denied |
| Planning/tools | Fixed safe tool sequence: read source, invoke structured provider, parse syntax, build patch; no arbitrary model-selected host tools |
| Provider interchangeability | Existing ModelProfile/ModelAdapter/ModelRegistry/BudgetedPlanner reused; compatible llama.cpp and native Ollama profiles |
| Routing/fallback | Explicit primary and optional fallback; context capacity checked before invocation; no hidden external fallback |
| Model correction | At most two actual invocations total; validation errors included in the next attempt; transport's nested automatic retry disabled for this loop |
| Proposal validation | Structured schema, selected paths, distinct edits, Python AST parsing without execution, nonempty patch, content/size/secret-pattern bounds |
| Persistent checkpoints | SQLite engineering_runs + durable events/attempts; same persistence and approval infrastructure as existing owner planning |
| Cancellation | Stored cancellation wins a compare-and-swap; late model outputs cannot approve/stage a result; request may finish within its transport timeout |
| Restart recovery | Active work becomes interrupted, no automatic model replay; explicit retry creates a fresh task |
| Approval | Exact source/model/budget/edits/expiry digest; source/configuration revalidated before approval/export |
| Patch export | Authenticated download, original source untouched; portable unified diff, LF/CRLF preserved |
| Authentication | New local launcher prints an ephemeral high-entropy session; bearer + literal loopback host + same-origin checks; existing owner password/session system unchanged |
| Observability/limits | Real stored stages, attempts, usage, failure categories, history, context/output/edit/request bounds and single-process/request leases |
| Local runtime quality | CPU Qwen2.5-Coder 0.5B is verified for a narrow guided edit; no general benchmark or frontier-quality claim |
| Optional external adapters | OpenAI/Anthropic/Gemini existing wire adapters are contract-tested; keys/budgets/per-task consent required; live paid-provider acceptance unverified |
| Linux support | Portable source/HTTP contracts and packaging checked in Linux CI; no live Linux model-through-workspace acceptance claimed |
| Automated candidate tests | **Disabled** for model proposals; parsing source is not runtime verification |
| Secure isolated worker | **Unverified and disabled**; PR #8 failures and Hyper-V evaluation preserved on their branches |
| Autonomous GitHub publication | **Disabled** behind the worker gate; developer release pushes/deployment do not activate that product feature |

The original three trusted fixture demonstrations can execute only audited catalog bytes.
They remain separate from local model proposals and never provide fallback AI responses.
Old issue-to-PR recordings must not be mistaken for a completed real-model isolated workflow.

The new local source mode supports proposals within selected Python files (up to 8 supplied,
4 edited), not arbitrary languages, full-repository context, new file creation, dependency
installation or host command execution. AST-valid output may still be incorrect or malicious;
review and testing remain the user's responsibility. Pattern scanning is not comprehensive DLP.

See [self-hosted setup](self-hosted.md), [security](security.md) and the release evidence for
executed checks and limitations. No private PC endpoint or credential is published.
