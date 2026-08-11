# Long-Running Tasks

## Example 1 — Valid vs. invalid state transitions

Input:
`PENDING -> COMPLETED` directly (skipping planning/running).

Expected:
- `InvalidTransitionError` raised — matches Section 30's exact state machine
  (`PENDING -> PLANNING -> RUNNING -> ... -> COMPLETED`); a task can never
  silently skip states

## Example 2 — Checkpointing survives across transitions

Input:
A task's checkpoint set to `{"step": 2, "found": [...]}` mid-run.

Expected:
- Reading the task back (even via a fresh `TaskStore` wrapping the same
  connection) returns the same checkpoint — this is what allows a task like
  "research the top 10 AI PM companies" to resume from step 2 rather than
  restarting from scratch after an interruption

## Example 3 — Pause and resume

Input:
A `RUNNING` task is paused, then resumed.

Expected:
- `pause()` → `PAUSED`, `resume()` → back to `RUNNING` — both are just named
  wrappers around `transition()`, validated the same way as any other
  transition

## Example 4 — Retry respects a budget

Input:
A `FAILED` task retried repeatedly, exceeding `max_retries`.

Expected:
- Each successful retry increments `retry_count` and moves to `RECOVERY`
  (Section 30's failure branch: `FAILED -> RECOVERY -> RUNNING`)
- Once `retry_count >= max_retries`, `MaxRetriesExceededError` is raised —
  retries are bounded, not infinite (same guardrail philosophy as Milestone 5's
  `AgentBudget`)

## Example 5 — Progress is clamped to a valid range

Input:
`update_progress(task_id, 1.5)` or `update_progress(task_id, -0.5)`.

Expected:
- Stored progress is clamped to `[0.0, 1.0]` — a buggy caller reporting
  out-of-range progress can't corrupt the stored value into something a
  dashboard would render nonsensically

## Example 6 — Tasks persist across process restarts

Input:
A task created via one `TaskStore` instance, read back via a fresh instance
wrapping the same connection/database file.

Expected:
- Full round-trip fidelity (state, checkpoint, retry count, progress,
  dependencies) — this is what makes "long-running" meaningful; an in-memory-only
  task store couldn't survive the kind of interruption long tasks are expected
  to survive

## Required fields (Section 31)

Every `LongRunningTask` carries `task_id`, `state`, `checkpoint`, `created_at`,
`updated_at`, `owner`, `retry_count`, `progress`, `dependencies`, `result` —
matching Section 31's list exactly.
