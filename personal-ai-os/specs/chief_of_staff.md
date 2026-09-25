# Chief of Staff (Phase 4, Milestones 32-43)

## Example 1 — Proactive Daily Brief is signal-driven, not manually assembled

Input:
Ranked `ScoredSignal`s from the Attention Engine (Milestone 31).

Expected:
- `generate_proactive_daily_brief()` derives priorities directly from ranked
  signals — unlike Phase 3's `daily_brief.py` (manually-assembled source
  strings), this is what makes it genuinely proactive
- Empty signal list returns an empty brief without calling the LLM at all

## Example 2 — Commitment detection and follow-up

Input:
"I'll send the report by Friday." / "They said they'd get back to me with pricing."

Expected:
- `detect_commitments()` distinguishes `USER` commitments from `OTHER_PARTY`
  commitments — an LLM call, since recognizing a commitment in natural
  language is a judgment call, not a pattern match
- `CommitmentStore.overdue()` flags a past-due, still-open commitment
  deterministically (a date comparison), never an LLM judgment — no reason to
  use an LLM for "is today after this date"

## Example 3 — Goal monitor bridges Phase 3 to Phase 4's event system

Input:
A CAREER-domain goal with a near deadline and low progress.

Expected:
- `GoalMonitor.check_goals()` turns goal state into `GOAL_UPDATED` events
  carrying `days_remaining`/`progress`/`domain` — feeding directly into
  Milestone 30's `GoalDeadlineApproachingTrigger` without reimplementing
  risk-scoring logic
- `ProactiveDomainAgent` filters these events to one domain using the real
  `domain` payload field — a genuine filter, not a stub that always passes

## Example 4 — Autonomous research runs as a tracked, resumable task

Input:
"Research the top 10 AI PM companies" (Phase 2's own worked example for
long-running tasks).

Expected:
- `AutonomousResearchRunner` drives `ResearchAgent` through the exact
  `LongRunningTask` state machine from Phase 2 Milestone 26 (PENDING ->
  PLANNING -> RUNNING -> EVALUATING -> COMPLETED, or -> FAILED on error) —
  not a new, parallel task abstraction

## Example 5 — Action plans are proposed, never auto-executed

Input:
A signal about a stakeholder needing a response.

Expected:
- `propose_plan()` returns an `ActionPlan` whose steps all start `PENDING`
- Any hallucinated tool name (not in `available_tool_names`) is dropped from
  the plan outright — never proposed, let alone executed
- `execute_step()` routes through Phase 2's `PolicyEngine` exactly as any
  other action would: READ steps run immediately (audited); WRITE/ACT steps
  raise `ApprovalPending` and require `resume_step()` — Phase 4's rule ("AI
  should not directly execute consequential actions") is enforced by reusing
  the existing approval gate, not a new bypass

## Example 6 — Outcome tracking is distinct from per-call verification

Input:
An executed action whose real-world effect (did the stakeholder actually
reply?) isn't knowable at execution time.

Expected:
- `Outcome` starts `PENDING` and is `resolve()`d later, separately from
  `PolicyEngine`'s immediate `verified` flag (Phase 2, Milestone 25) — one
  checks "did the tool call return something," the other checks "did this
  actually work," which can only be known after time passes
- `success_rate()` returns `None` (not `0.0`) until something has actually
  resolved — an unmeasured system should never look like a failing one

## Example 7 — Personal Decision Engine only ever proposes a decision

Input:
A high-attention signal.

Expected:
- `DecisionEngine.decide()` returns one of `NO_ACTION`/`NOTIFY_ONLY`/
  `PROPOSE_PLAN`/`ESCALATE` plus reasoning — never executes anything itself
- The signal id is always taken from the real signal, never trusted from the
  LLM's own output, even though the LLM is never actually asked to produce
  one (defense in depth against a future prompt change asking for it)

## Example 8 — Scheduling logic is real; the always-on process is not

Input:
An `INTERVAL` job with a 1-hour period, and an `EVENT_DRIVEN` job.

Expected:
- `Scheduler.due_jobs()`/`tick()` correctly determine whether enough time has
  elapsed since last run — genuine, tested logic
- `notify_event()` runs `EVENT_DRIVEN` jobs on demand, never on a timer
- Per project scope decision, nothing in this codebase calls `tick()` on an
  actual wall-clock timer forever — that wiring (a cron entry, a background
  thread) is deferred; the scheduling *logic* itself is complete and tested

## Example 9 — Chief of Staff Orchestrator only sequences existing components

Input:
An urgent-email event.

Expected:
- `ChiefOfStaffOrchestrator.process()` runs events through
  `TriggerEngine.evaluate()` -> `AttentionEngine.rank()` ->
  `DecisionEngine.decide()` -> (if `PROPOSE_PLAN`) `propose_plan()` — every
  step delegates to an already-tested component; the orchestrator has no
  trigger-matching, scoring, or plan-generation logic of its own

## Example 10 — Proactive evaluation reports false positive/negative separately

Input:
Labeled cases where a signal fired but shouldn't have (annoying), and cases
where a signal should have fired but didn't (missed).

Expected:
- `compute_false_rates()` reports `false_positive_rate` and
  `false_negative_rate` as two distinct numbers, never blended into one
  "accuracy" score — a proactive system's two failure modes have very
  different costs (annoyance vs. missing something important) and must stay
  separately visible

## Example 11 — Chief of Staff Dashboard is data-only

Input:
Commitment and outcome stores with a mix of open/overdue/resolved records.

Expected:
- `get_chief_of_staff_snapshot()` reports open/overdue commitment counts,
  pending outcomes, and success rate — same "data layer only, no UI" scope
  decision as Phase 2 Milestone 29 and Phase 3's dashboard extensions

## Scope decisions carried through this milestone batch

- No real always-on scheduler/poller exists (Milestones 30, 39) — events are
  fed in explicitly; the logic that would run on a schedule is real and tested.
- `ChiefOfStaffOrchestrator` never calls `execute_step`/`resume_step` itself —
  APPROVE/ACT/VERIFY remain the caller's responsibility, consistent with Phase
  4's rule that AI should not directly execute consequential actions.

## Example 12 — Activating Chief of Staff against real goal data

The user asked to "activate the chief of staff now... chief of staff needs
to track progress against all 15 project based learning goals." Checked
first: `GoalMonitor` (bridges `GoalStore`/`GoalAgent` to `GOAL_UPDATED`
events) existed and was tested, but was never run against real seeded goal
data — only exercised in isolation by tests.

New `scripts/run_chief_of_staff.py` wires the real, already-tested pipeline
end to end for the first time: `GoalStore` (15 real learning goals) ->
`GoalAgent.recommend_priorities()` -> `GoalMonitor.check_goals()` ->
`TriggerEngine` -> `AttentionEngine` -> `DecisionEngine` (1 real LLM call
per surfaced signal) -> `ChiefOfStaffOrchestrator`.

A real gap was found while wiring this: all 15 learning goals were
deliberately seeded with no deadline (the user's own earlier choice), so
`GoalDeadlineApproachingTrigger` (which only ever evaluates deadline
proximity) can never fire for any of them. New `StalledGoalTrigger` in
`app/proactive/builtin_triggers.py` fires instead when a goal has no
deadline, is below a progress threshold, and hasn't been updated recently
— reusing the same `GOAL_UPDATED` event `GoalMonitor` already produces
(`GoalMonitor` now additionally includes `updated_at` in that event's
payload, additive/backward-compatible). Given its own base attention
weight (0.5, deliberately lower than an actual deadline-approaching signal's
0.9).

Also: the user asked Chief of Staff to track progress on the 15 learning
goals, which required an actual assessment of where the project stands on
each capability. Progress values were updated from the original all-0.0
seed to a real, evidence-based code-coverage-proxy assessment (e.g. AI
Evaluation and RAG scored highest given how much of each is actually built
and tested; Multimodal AI and AI Product Strategy scored lowest) — each
value's justification is recorded directly on the goal
(`success_criteria`'s `[Progress basis]` entry), and the assessment is
explicitly labeled throughout as a proxy for the user's own personal
understanding, not a claim to observe it.

Verified live end to end against the real Gemini API: a verification run
(with `staleness_days=0`, without touching the real seeded `updated_at`
values) confirmed the full pipeline actually fires for real
below-threshold goals, correctly scores them, and produces genuine
per-signal `DecisionEngine` reasoning (e.g. "the goal is stalled at 55%
with no recent updates and no deadline, warranting a low-urgency
notification"). A real run against the actual seeded data (all goals
&lt;7 days old) correctly produced zero signals — an honest, correct
outcome, not a bug, documented as such in the script's own output.
`StalledGoalTrigger`: 4 new tests (fires when stale+low-progress, doesn't
fire when recently updated, doesn't fire when progress is high, defers to
the deadline trigger when a deadline exists). 738 tests passing (was 733).
