# Context Engineering

## Example 1 — Ordering is configurable, not hardcoded append

Input:
Sections for system, memory, retrieved_context, tool_results, history, user,
built with two different `order` configurations.

Expected:
- Output text reflects the configured order, not insertion order
- Section 27's two example orderings (system/user/memory/retrieved/tools/history
  vs. system/user/history/retrieved/memory) are both expressible via `order=[...]`

## Example 2 — Sections outside the configured order are dropped

Input:
A section named "debug_info" not present in `ContextBuilder.order`.

Expected:
- It never appears in the built prompt (Section 26: the builder decides what
  enters context, not "append everything")

## Example 3 — Empty sections are omitted

Input:
A "memory" section with empty content (no memory available yet).

Expected:
- The `### memory` header does not appear at all — avoids wasting tokens on
  empty sections

## Example 4 — Compression under token budget

Input:
`max_tokens` set below the total size of all sections combined.

Expected:
- Lowest-priority sections (highest `priority` number) are dropped first
- Higher-priority sections (e.g. `system`) are preserved even under a tight budget
- Surviving sections keep their original relative order (Section 29)

## Example 5 — Lost-in-the-middle experiment harness

Input:
A critical fact inserted at `start`, `middle`, or `end` of filler content via
`build_positioned_context()`.

Expected:
- The harness reliably places the fact at the requested position, so answer
  quality can be measured per-position with a real LLM (Section 28) —
  this milestone builds the harness; running it against Gemini to measure
  actual degradation is a follow-up experiment, not something a unit test
  can assert on its own.

## Failure case — Invalid position argument

Expected:
- `ValueError` raised for any position other than `start`/`middle`/`end`
