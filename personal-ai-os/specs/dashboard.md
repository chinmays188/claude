# Personal AI Dashboard (data layer)

## Scope decision

Per project decision, this milestone builds the **data layer only** — queryable
functions producing exactly the data Section 38's example dashboard displays,
not a Streamlit/web UI. The functions are the reusable, testable core; wiring
them into a real UI is a thin follow-up (a Streamlit script calling these
functions and rendering the result).

## Example 1 — Today's Activity block matches Section 38 exactly

Input:
A day's traces, audit log, and task store.

Expected:
- `get_todays_activity()` returns `agent_runs`, `tasks_completed`,
  `pending_approvals`, `evaluation_score`, `avg_latency_ms` — the exact fields
  in Section 38's example (`Agent Runs 14`, `Tasks Completed 11`, etc.)
- With zero traces, `evaluation_score`/`avg_latency_ms` are `None`, not `0` —
  "no data yet" must be distinguishable from "score of zero"

## Example 2 — Memory block matches Section 38 exactly

Input:
A populated `PersistentMemoryStore` (Milestone 20) and `GraphStore`
(Milestone 27).

Expected:
- `get_memory_summary()` returns `memories`, `decisions`, `projects` — reusing
  Milestone 20's `count()` and Milestone 27's `nodes_by_type()` rather than
  querying SQLite directly a second time

## Example 3 — AI Health block reflects real eval results

Input:
Groundedness/tool-success/retrieval-recall scores and a regression pass/fail
flag, as already computed by Phase 1's evaluation modules (Milestones 8, 11).

Expected:
- `get_ai_health()` shapes already-computed results into the dashboard's
  schema — it does not itself run any evaluation. `regression_status` is
  `"UNKNOWN"` until a real regression result is supplied, never defaulted to
  `"PASS"` (an untested system should never *look* healthy by default)

## Example 4 — Full snapshot assembly

Input:
All of the above, for one user.

Expected:
- `get_dashboard_snapshot()` composes all three blocks into one
  `DashboardSnapshot` — the single call a UI layer would actually make

## Non-goals for this milestone

- No Streamlit/web UI — per project scope decision, this is data plumbing only.
- No historical time-series (Section 38's blocks are a point-in-time snapshot,
  not a trend chart) — trending would require a dedicated metrics-over-time
  store, not built here.
- `get_todays_activity()` filters "today" using each task's `updated_at` date;
  `Trace` (Phase 1, Milestone 12) has no wall-clock date field, so the caller
  is responsible for pre-filtering traces to the desired day before calling —
  this is a known interface gap, not silently glossed over.
