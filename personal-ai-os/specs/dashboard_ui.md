# Dashboard UI (portfolio MVP)

## Scope decision

Streamlit, matching Section 5's original stack table ("Visualization:
Streamlit initially"). Built as a portfolio-facing MVP first (per project
decision), but designed to grow into daily use rather than be throwaway: it
reads the real SQLite stores directly, so real usage of the CLI/voice
interface naturally populates it over time, replacing/extending the seeded
demo data rather than requiring a separate "real" version later.

## What was built

- `scripts/seed_demo_data.py`: populates the real stores (`PersistentMemoryStore`,
  `GoalStore`, `GraphStore`, `TaskStore`, `AuditLog`, `CommitmentStore`,
  `OutcomeStore`) with fabricated, realistic demo data — consistent with the
  project's synthetic-data-only convention for domain workflows.
- `dashboard_app.py`: a Streamlit app with 6 pages (Overview, Career, PM,
  Finance, Learning, Chief of Staff), each backed directly by an existing,
  already-tested `app/dashboard/*.py` function. No new backend logic exists
  in this UI layer at all.
- `app/dashboard_ui/demo_workflow_outputs.py`: fabricated values for the
  dashboard fields that are caller-supplied from domain workflow outputs
  rather than persisted anywhere (e.g. `resume_readiness`, feedback themes,
  portfolio allocation) — kept in one clearly-labeled module, separate from
  the real persisted data the seed script writes.
- `.streamlit/config.toml`: binds the server to `localhost` only. Without
  this, Streamlit defaults to binding all interfaces (`0.0.0.0`) — caught
  during manual testing when the server printed a `Network URL`/`External
  URL` briefly reachable from the local network.

## Example 1 — Every page renders from real, already-tested functions

Input: `dashboard_app.py`'s six `render_*` functions.

Expected:
- Each calls exactly one `app/dashboard/*.py` function (e.g.
  `render_finance` calls `get_finance_dashboard`) and only formats the
  result — verified by running all 6 render functions directly (bypassing
  Streamlit's script-runner context) and confirming none raise

## Example 2 — The seed script populates data the dashboard functions can actually read back

Input: `scripts/seed_demo_data.py --db <path>`.

Expected:
- Writing memories, goals, graph nodes/decisions, a completed task, an
  audit-log entry, commitments, and outcomes, then reading them back through
  `get_memory_summary`/`get_todays_activity`/`get_career_dashboard`/
  `get_chief_of_staff_snapshot` returns non-zero/populated results
- A real inconsistency was caught while wiring this up: Phase 2's
  `get_memory_summary()` counts `NodeType.DECISION` graph *nodes*, while
  Phase 3's richer `Decision` model lives in a separate `decisions` table —
  the two are not the same underlying data. Fixed by having the seed script
  write both a `Decision` record (via `add_decision()`) and a matching
  `GraphNode(type=DECISION)` for each seeded decision, so both
  representations reflect real demo data rather than silently disagreeing.

## Example 3 — The server binds to localhost only

Input: `streamlit run dashboard_app.py`.

Expected:
- Server output shows a single `URL: http://localhost:<port>` line, with no
  `Network URL`/`External URL` — confirmed by actually starting the server
  and inspecting its own log output, both with and without
  `.streamlit/config.toml` present (the fix was verified against the actual
  problem it fixes, not assumed)

## Example 4 — Traces page reads real, persisted live-request traces

Input: `scripts/trace_request.py "<request>"`, followed by opening the
dashboard's Traces page.

Expected:
- `trace_request.py` now wraps its real run (router + tool agent, live
  Gemini calls) in `app/observability/traces.py`'s `TraceRecorder`, and
  persists the resulting `Trace` (routing decision, real tool-call
  input/output as span metadata, real per-call token usage, real summed
  cost) to `data/personal_ai.db` via the new `app/observability/trace_store.py`
  (`TraceStore`), keyed by `trace.execution_id` (the trace_id printed at the
  end of the run)
- The dashboard's Traces page lists every saved trace_id in the sidebar
  (newest first) and lets a trace_id be pasted directly into a search box;
  selecting one renders its full stored trace — status, latency, cost,
  token counts, and every span (with tool-call args/results as span
  metadata) — with no live LLM call made by the dashboard itself
- Verified live end-to-end: ran `trace_request.py` against a real request,
  confirmed the trace persisted with correct spans/cost via `TraceStore`
  directly, then confirmed the dashboard's listing + lookup-by-id logic
  returns the same data

**Deployment scope, decided explicitly with the user**: this page is a
local dev/demo feature only. Streamlit Community Cloud's filesystem is
ephemeral and separate from your local machine's `data/personal_ai.db`, and
the public deployment intentionally has no `GEMINI_API_KEY` configured (see
Non-goals below) — so traces run locally will only ever show up when the
dashboard is also run locally against the same DB file. No Gemini key was
added to the public deployment to enable this; that would reopen the
"dashboard never makes live LLM calls" decision for a public, cost-exposed
app.

## Non-goals for this MVP

- No interactivity beyond viewing — no in-UI action approval, no
  triggering a workflow from a button. The dashboard is read-only,
  consistent with every dashboard milestone across Phases 2-4 being
  "data layer only."
- No authentication on the dashboard itself — it's a local, single-user
  portfolio demo; Phase 5's `app/platform/auth.py` exists but isn't wired
  into this UI.
- Career/PM/Finance/Learning fields sourced from domain workflow outputs
  (resume readiness, feedback themes, etc.) use fabricated demo values
  rather than actually invoking each domain's real LLM-driven workflow on
  every page load — doing so would mean a live Gemini API call (and cost)
  every time the dashboard renders, which isn't the right tradeoff for a
  page that's refreshed frequently during a demo.
