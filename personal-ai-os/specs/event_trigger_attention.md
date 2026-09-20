# Event & Trigger Engine + Personal Attention Engine (Phase 4, Milestones 30-31)

## Scope decision

Events are fed into `EventBus.publish()` explicitly (by a test, a manual call,
or a Phase 2 integration's own result) rather than sourced from an always-on
background poller — this sandbox has no long-lived process to host real
continuous polling, per project scope decision. The event/trigger/attention
logic itself is real and fully testable; only the "who calls publish() on a
schedule" wiring is deferred.

## Example 1 — Event bus delivers to the right subscribers only

Input:
A `TASK_STATE_CHANGED` event published with one subscriber on that type and
one on `EMAIL_RECEIVED`.

Expected:
- Only the `TASK_STATE_CHANGED` subscriber receives it
- Multiple subscribers on the same type all receive the same event

## Example 2 — A trigger only fires when its rule actually matches

Input:
A `TASK_STATE_CHANGED` event reporting a task stuck in `RUNNING` for 30 hours,
against `TaskStuckTrigger(stuck_threshold_hours=24)`.

Expected:
- `evaluate()` returns a `Signal`; below the threshold, or for the wrong
  event type, it returns `None`
- Trigger rules are deterministic (state + duration/threshold comparisons),
  not LLM calls — "did this event match this pattern" should be cheap and
  auditable; judgment about whether it's worth surfacing is the Attention
  Engine's job, not the trigger's

## Example 3 — Multiple triggers can independently fire on the same engine

Input:
A `TriggerEngine` holding `TaskStuckTrigger`, `GoalDeadlineApproachingTrigger`,
`UrgentEmailTrigger`; one event published.

Expected:
- Only the trigger(s) actually watching that event type and matching its
  content produce a signal — an event never fires triggers watching a
  different `EventType`

## Example 4 — Attention scoring uses deterministic, auditable weights

Input:
Signals from `goal_deadline_approaching` (weight 0.9) and `task_stuck`
(weight 0.6).

Expected:
- `AttentionEngine.rank()` sorts highest-attention-first
- Weights are a plain dict (`_TRIGGER_BASE_WEIGHT`), not an LLM judgment call —
  reviewable and adjustable directly, consistent with this project's
  preference for deterministic scoring wherever judgment isn't strictly needed

## Example 5 — Notification deduplication

Input:
The same signal (same trigger name + title) ranked twice.

Expected:
- The second occurrence is filtered out as a duplicate — the same underlying
  issue (e.g. the same stuck task) firing repeatedly should not re-notify the
  user every time the trigger re-evaluates
- Signals with different titles are never treated as duplicates of each other

## Non-goals for this milestone

- No real background scheduler/poller exists yet (Milestone 39: "Scheduled &
  Event-driven Agents" is a later, dedicated milestone) — this milestone is
  the event/trigger/attention *logic*, callable from wherever a scheduler
  eventually lives.
- Trigger rules here are illustrative (task-stuck, goal-deadline, urgent-email)
  covering the event types already producible by Phase 2/3 — a comprehensive
  trigger library covering every possible signal is not attempted.
