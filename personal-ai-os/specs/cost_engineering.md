# Cost Engineering

## Example 1 — Journey cost, not just model cost

Input:
A "career research" journey: orchestrator classification call + research agent call,
both on the same model.

Expected:
- `CostTracker.journey.total` answers "how much did this whole journey cost",
  not just "how much did model X cost" (Section 49)

## Example 2 — Cost breakdown by component

Input:
The same journey as Example 1.

Expected:
- `journey.by_component()` shows cost per component (orchestrator vs. research_agent
  vs. evaluator), matching Section 50's dimension list

## Example 3 — Cost breakdown by model

Input:
A journey using two different models (a cheap classifier model, a stronger
research model).

Expected:
- `journey.by_model()` shows cost attributed to each model separately — this is
  what would let you answer "is the stronger model actually worth its cost?"
  (Section 37/50)

## Example 4 — Free/local components still appear in the breakdown

Input:
A journey step that costs nothing (local calculator tool, local FAISS retrieval).

Expected:
- `record_zero_cost()` still adds a line item at $0 — the breakdown stays complete
  rather than silently omitting free steps, so "what did this journey actually do"
  is fully visible even where cost is zero

## Example 5 — Unknown model rate

Input:
A component recorded against a model with no configured `CostRate`.

Expected:
- Cost defaults to 0.0 rather than raising — an unconfigured rate should not
  crash the whole journey's accounting, but it is visible as $0 (not silently
  dropped from the breakdown), so a missing rate config is discoverable

## Non-goal for this milestone

- Currency/rate values here are illustrative placeholders — real per-model rates
  (Section 50 example uses ₹) are a configuration concern, not hardcoded in this
  library.
