# Personal Context Engine

## Example 1 — NONE-importance items never enter context

Input:
An "unrelated conversation" item marked `importance=NONE` alongside a genuinely
relevant item.

Expected:
- `PersonalContextEngine.select()` excludes the NONE item outright, regardless
  of how high its relevance score might otherwise be — matches Section 20's
  exact example table (`Unrelated conversation -> NONE`)

## Example 2 — Each scoring dimension moves the ranking independently

Input:
Two items identical except for one dimension (relevance, importance, freshness,
or confidence).

Expected:
- Isolating each weight to 1.0 and the rest to 0 demonstrates that dimension
  alone changes the ranking (see the four per-factor tests in
  `test_personal_context_engine.py`) — proves the scoring function actually
  uses all of Section 20's fields, not just relevance

## Example 3 — Token budget is respected under selection

Input:
10 candidate items, each costing 100 tokens, budget of 250 tokens.

Expected:
- `select()` never returns a set whose combined `token_cost` exceeds the budget
  — greedy highest-score-first selection, skipping items that would blow the
  budget rather than stopping at the first one that doesn't fit

## Example 4 — Context experiments are comparable across a common set of metrics

Input:
Multiple named variants (e.g. "system-first ordering" vs. "history-first
ordering", or "no compression" vs. "compressed").

Expected:
- `compare_variants()` reports accuracy, groundedness, latency, token usage,
  and cost per variant, and `.best_accuracy` / `.fastest` / `.cheapest` /
  `.ranked_by()` let a caller ask concrete comparison questions instead of
  eyeballing a table — matches Section 21's exact metric list

## Relationship to Phase 1

- `app/context/lost_in_middle.py` (Phase 1, Milestone 10) already provides the
  lost-in-the-middle experiment harness Section 21 calls for — reused as-is,
  not rebuilt.
- `PersonalContextEngine` operates one level below `ContextBuilder`
  (Phase 1): it scores and selects individual *items* (memories, chunks, tool
  results); `ContextBuilder` then assembles the selected items' text into named,
  ordered, budget-compressed *sections*. The two compose rather than duplicate
  each other's job.

## Non-goals for this milestone

- Retrieval order / memory order / tool-result placement experiments (also
  listed in Section 21) are expressible via `ContextBuilder.order` (Phase 1)
  and measurable via `compare_variants()`, but no specific pre-built experiment
  results are included here — running them against real data is follow-up work.
