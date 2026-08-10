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
