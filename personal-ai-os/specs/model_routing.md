# Model Routing

## Example 1 — Simple task routes to the cheap model

Input:
A classification task (`TaskComplexity.SIMPLE`).

Expected:
- `ModelRouter.route()` returns the lite/cheap-tier provider
- Matches Section 37's table: `Simple task -> Flash-Lite`

## Example 2 — Complex task routes to the stronger model

Input:
A generation task (`TaskComplexity.COMPLEX`) — e.g. producing a research/analysis/
planning answer.

Expected:
- Returns the stronger-tier provider
- Matches Section 37: `Complex task -> Flash`

## Example 3 — Evaluation routes to the stronger model

Input:
An LLM-as-judge scoring task (`TaskComplexity.EVALUATION`).

Expected:
- Returns the stronger-tier provider (Section 37: `Evaluation -> Flash`) — judging
  quality is treated as a complex task, not delegated to the cheapest model

## Failure case — Incomplete router configuration

Input:
A `ModelRouter` constructed without a provider for every `TaskComplexity` value.

Expected:
- `ValueError` raised at construction time, naming the missing tier(s) — a routing
  gap should fail loudly at startup, not silently at the first request that hits
  the missing tier

## Scope note

Both tiers here are Gemini models (per the project's decision to stay within
Section 8's "must run on Gemini alone" constraint) — e.g. `gemini-3.5-flash-lite`
for SIMPLE, a stronger Gemini model for COMPLEX/EVALUATION. This demonstrates real
routing logic without requiring a second provider (OpenRouter) or API key.
`ModelRouter` is provider-agnostic, so adding a second real provider later
(Milestone 8's stack table) requires no changes to this file.

Not yet wired into `Orchestrator`/`main.py` — exists as a standalone, tested
component ready for that integration, consistent with how hybrid retrieval and
context engineering were left in Milestones 9-10.

## Example 4 — Actually wired into Orchestrator, with a real degraded-mode path

Closes this spec's own long-standing disclosed gap ("Not yet wired into
Orchestrator/main.py"). The user asked directly: "we are only using
gemini for LLM call. what all needs to be done to take the progress to
90%." Checked first, honestly: this exact `ModelRouter`/`TaskComplexity`
scaffold and `FallbackProvider` (a separate real, tested component) were
both still unused in any real code path.

`Orchestrator` gained a new, optional `agent_llm` param: classification/
planning calls (`UnifiedRouter`, `MultiAgentPlanner`) always use the main
`llm` — never routed, since classification never benefits from a
stronger model and shouldn't spend a routed tier's real, scarce daily
quota. The 3 agents' own generation calls use `agent_llm` when given,
defaulting to `llm` (every existing caller's behavior unaffected,
confirmed by every pre-existing `Orchestrator` test passing unchanged).

New `RoutingLLMProvider` implements `LLMProvider` directly by wrapping a
`ModelRouter`: `classify_task_complexity()` (free, deterministic — a
signal phrase or ≥30 words, mirroring
`app/agents/multi_agent_coordinator.py`'s `might_need_multiple_agents()`
pattern) picks `SIMPLE` or `COMPLEX`; `SIMPLE` goes straight to the cheap
tier (`gemini-3.5-flash-lite`, this project's existing default);
`COMPLEX` goes through a real `FallbackProvider([strong, cheap])` — the
strong tier (`gemini-3.8-flash`) is a real, distinct, pricier tier with a
real, hard free-tier quota (20 requests/day, confirmed earlier this
project). Every call records a real, inspectable `RoutingDecision`
(complexity, model_name, degraded, reason).

**Verified fully live, not simulated**: while generating the committed
dashboard examples (`scripts/generate_model_routing_examples.py`), the
strong tier genuinely returned a real `503 UNAVAILABLE` (external API
capacity, consistent with this project's documented history of
intermittent Gemini capacity issues — not a code bug), and the real
`FallbackProvider` genuinely degraded to the cheap tier with the real
error recorded in the decision's `reason`. A separate, explicitly-labeled
simulated-failure example (a scripted failing provider, not real quota
exhaustion) demonstrates the same degraded path without spending more of
the scarce real daily quota — confirmed with the user this trade-off was
acceptable rather than deliberately burning the rest of the day's quota.

New dedicated "Model Routing" dashboard page: its own architecture
diagram, a live (free, no LLM call) complexity-classification demo the
user can type into, and the 3 committed real examples (SIMPLE→cheap,
COMPLEX→strong with a real fallback, and one simulated-failure
comparison) with real per-call token usage shown.

Explicitly NOT done, disclosed honestly: both tiers are still Gemini —
the "free/open-source model" criterion (e.g. a local Ollama model) was
deferred by an explicit scope decision, not built, to avoid a new
install/dependency in this round.

837 tests passing (was 833).
