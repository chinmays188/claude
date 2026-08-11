# Personal Event & Decision Graph

## Example 1 — Nodes and relationships

Input:
A `PERSON` node ("Alice") connected to a `PROJECT` node ("Personal AI OS") via
a `works_on` edge (Section 32's example: `User -> Career -> Projects -> AI PM`).

Expected:
- `GraphStore.neighbors()` traverses the edge and returns the connected node

## Example 2 — Decision record matches Section 33's exact schema

Input:
A decision: "Use RAG for spec Q&A," with context, reason, alternatives
considered, the chosen option, and expected outcome.

Expected:
- `Decision` carries every field Section 33 lists:
  `decision, date, context, reason, alternatives, chosen_option,
  expected_outcome, actual_outcome, related_project`

## Example 3 — "Why did I make this decision?"

Input:
A stored decision, queried by id.

Expected:
- `GraphStore.why()` answers Section 33's exact named question — assembling
  the decision's context, reason, chosen option, and (if known) actual outcome
  into a coherent explanation, not just dumping raw fields

## Example 4 — Decisions scoped to a project

Input:
Two decisions, only one linked to a given project via `related_project`.

Expected:
- `decisions_for_project()` returns only the linked one — this is what would
  let "why did I choose RAG for THIS project" stay scoped correctly once a
  user has decisions across many projects

## Example 5 — Graph persists across process restarts

Input:
A node/decision written via one `GraphStore` instance, read via a fresh
instance wrapping the same connection.

Expected:
- Full round-trip fidelity — same durability guarantee as Milestone 20's
  `PersistentMemoryStore` and Milestone 26's `TaskStore`; a decision graph
  that resets every process run couldn't answer "why did I decide this last
  month"

## Non-goals for this milestone

- No graph traversal algorithms beyond direct neighbors (`neighbors()`) —
  multi-hop path-finding ("how is this decision connected to that goal
  through 3 intermediate nodes?") is not implemented.
- No automatic extraction of decisions/relationships from conversation —
  `Decision`/`GraphNode`/`GraphEdge` are written explicitly by the caller in
  this milestone, matching the storage layer's scope; feeding conversation
  through Milestone 20's `MemoryWritePolicy`-style classifier into graph
  writes is natural follow-up work, not built here.
