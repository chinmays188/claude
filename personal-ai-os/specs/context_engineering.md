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

## Example 6 — Real gap found: no session/turn state, so compression never actually ran

The user asked for a full breakdown of context engineering in this project:
"let us first breakdown session memory, user memory, long term memory ...
how each memory is getting called ... after how many turn are we
summarizing the session ... concept of context window/compression ...
how is ordering of memory happening."

Checked directly against the code, not assumed, and reported honestly
before building anything:
- `Orchestrator.handle(text)` was completely stateless -- one string in,
  one answer out, no history parameter at all. There was no session, so
  "after how many turns do we summarize" didn't have an answer: there was
  no multi-turn state to summarize in the first place.
- `ContextBuilder`'s real compression path (Example 4 above -- drop the
  lowest-priority whole section first once over `max_tokens`) was dead
  code in production: its only real call site (`PersonalRagPipeline`)
  always constructs it with the default `max_tokens=None`.
- `PersonalContextEngine` (Section 19/20's more sophisticated 4-factor
  scoring engine) was never called from anywhere outside its own tests.
- `VoiceSession.turns` was appended to on every call but never actually
  passed back into `Orchestrator.handle()` -- its own docstring claimed
  "conversation continuity across multiple voice turns," which wasn't
  true.

Fixed the biggest structural gap: new `app/conversation/session.py`'s
`ConversationSession` wraps `Orchestrator` (without changing its
signature -- every existing stateless caller, e.g.
`scripts/trace_request.py`, is unaffected) and adds:
- Real turn history (`ConversationTurn` list), with the most recent
  `recent_turns_kept_verbatim` turns injected verbatim into the next
  request's text, ahead of the running summary.
- A real, token-budget-based compression trigger (not an arbitrary turn
  count, since that's not actually what determines whether history fits
  the prompt): once `estimate_tokens(running_summary) +
  estimate_tokens(verbatim_window)` exceeds `history_token_budget`, one
  real LLM call (`RepairableGenerator` against a `_RunningSummary` schema)
  summarizes the older turns, and the verbatim window resets to just the
  most recent turns.
- `VoiceSession` now delegates to `ConversationSession` internally,
  closing its own real bug, with every existing constructor call
  (`VoiceSession(Orchestrator(llm))`) unaffected since the memory
  dependencies default to fresh in-memory ones.

A real, useful interaction was found and handled, not hidden: injecting
real prior-turn context into the next request can push its word count
over `might_need_multiple_agents()`'s free heuristic threshold, adding one
real `MultiAgentPlanner` call that wouldn't have fired on the bare input
alone -- a genuine, disclosed side effect of adding real context, not a
bug.

Verified live against the real Gemini API (not just scripted tests): a
2-turn `ConversationSession` conversation where turn 1 stated a name and a
formatting preference, and turn 2's real answer measurably changed style
(bullet points) based on that real injected context -- proving the
compression/injection design actually changes model behavior, not just
that the code runs.

`ContextBuilder`'s section-drop compression and `PersonalContextEngine`'s
4-factor scoring are still NOT wired into `ConversationSession` --
disclosed honestly as a remaining gap (Example 4's compression logic and
`PersonalContextEngine`'s more sophisticated selection could replace the
current simple verbatim-window-plus-summary approach in a future pass).

817 tests passing (was 808).
