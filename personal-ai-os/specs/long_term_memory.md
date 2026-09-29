# Long-Term Memory

## Example 1 — Not every conversation becomes memory

Input:
"What's the weather?" — a one-off question with no lasting personal relevance.

Expected:
- `MemoryWritePolicy.evaluate()` classifies `should_remember=false`
- Returns `(None, False)` — nothing written, no approval needed (Section 12:
  "the system must NOT save every conversation")

## Example 2 — A real decision gets remembered

Input:
"We decided to use RAG over fine-tuning because the doc changes too often."

Expected:
- Classified as `type=decision`, a reasonable `importance`
- Passes the importance threshold and duplicate check → returned as a candidate
  ready to persist

## Example 3 — Below-threshold importance is dropped

Input:
A classifier result with `importance=0.1` against a `0.3` threshold.

Expected:
- Treated the same as "not worth remembering" — low-importance content doesn't
  silently accumulate forever

## Example 4 — Duplicate content is not re-saved

Input:
A new candidate whose summary exactly matches (case/whitespace-insensitive) an
existing memory's summary.

Expected:
- Rejected before writing — `is_duplicate()` is the dedup gate from Section 12's
  pipeline

## Example 5 — High-importance memories require approval

Input:
A candidate with `importance=0.9` against a `0.7` approval threshold.

Expected:
- `requires_approval=True` — a major/sensitive memory isn't silently persisted
  without the user confirming it (Section 12: "User Approval if necessary")

## Example 6 — Memory persists across process restarts

Input:
A memory written via `PersistentMemoryStore`, then read back via a fresh store
instance wrapping the same SQLite connection/file.

Expected:
- The memory is still there — this is what makes it "long-term" rather than
  Phase 1's in-memory-only `MemoryStore` (which resets every process run)
- Still scoped by `(tenant_id, user_id)`, same isolation discipline as Phase 1
  (Section 55)

## Example 7 — Retrieval ranks by multiple factors, not similarity alone

Input:
Two memories with equal semantic similarity to a query, but one is more recent,
more important, or user-confirmed.

Expected:
- `MemoryRetriever.rank()` weighs semantic similarity, recency (exponential
  decay), importance, and confirmation together — matching Section 13's list —
  each factor demonstrably moves the ranking in isolation (see
  `test_memory_retrieval.py`'s per-factor tests)

## Non-goals for this milestone

- Duplicate detection is exact-match only; semantic duplicate detection (e.g.
  "learned Docker" vs. "picked up Docker basics" as the same underlying fact)
  is not implemented.
- "Current task relevance" (Section 13's 5th ranking factor) is left to the
  caller — this module doesn't know what the current task is.

## Example 8 — Real gap found: MemoryRetriever/MemoryWritePolicy existed but were never called live

Found while breaking down this project's context engineering for the
user (see specs/context_engineering.md's Example 6 for the full
breakdown): `MemoryRetriever` (Example 7's real 4-factor semantic
scoring) and `MemoryWritePolicy` (Example 5's real classify -> importance
-> duplicate-check -> approval-gate pipeline) were both real, tested, and
correct in isolation -- but neither was ever called from any live request
path. Only `naive_relevance.py` (explicitly documented in its own module
as keyword-overlap only, NOT semantic) was wired into
`scripts/trace_request.py`/`Orchestrator`.

Fixed by wiring both into the new `app/conversation/session.py`'s
`ConversationSession`:
- **Read side**: every turn calls `MemoryRetriever.rank()` against
  `PersistentMemoryStore.list_all()`, injecting the top-ranked real
  memories as plain-text context ahead of the current request -- real
  semantic scoring, not keyword overlap.
- **Write side**: after every turn, `MemoryWritePolicy.evaluate()` runs
  against the real exchange. A low-importance candidate is written
  immediately; a high-importance one (>= `approval_threshold`) is queued
  in `session.pending_memory_approvals`, never silently auto-written --
  `session.approve_pending_memory(turn_id)` is the explicit human approval
  path, mirroring `app/actions/policy_engine.py`'s propose/resume pattern
  exactly (Phase 4's standing human-in-the-loop principle, applied here
  too).

`naive_relevance.py` is NOT removed -- it's still what
`scripts/trace_request.py`'s stateless CLI path uses (that script has no
`ConversationSession`, by design, since it's meant to show one ad hoc
request's real routing/tool-calling/cost, not multi-turn behavior).

Verified fully live against the real Gemini API: a real 2-turn
conversation stating "My name is Chinmay and I prefer short, bullet-point
answers" was classified by the real `MemoryWritePolicy` LLM call as
`importance=0.8` (a preference + identity fact) and correctly queued for
approval rather than auto-written; calling `approve_pending_memory()`
then wrote it as a real, persisted `MemoryRecord`. No number or outcome
here was scripted for this particular verification run.

817 tests passing (was 808).
