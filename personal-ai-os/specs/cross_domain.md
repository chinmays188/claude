# Cross-Domain Layer

## Example 1 — Goal tracking with Section 33's exact fields

Input:
A career goal ("Get AI PM role") with priority, deadline, dependencies.

Expected:
- `Goal` carries every field Section 33 lists: `goal_id, title, description,
  domain, priority, deadline, status, progress, dependencies, success_criteria`
- Persisted via `GoalStore` (SQLite-backed, same durability guarantee as
  Phase 2's `TaskStore`/`GraphStore`) — a goal-tracking system that resets
  every process run isn't meaningfully "tracking" anything

## Example 2 — Dependency resolution (Section 34)

Input:
"Prepare for AI PM interviews" depends on "Resume complete" (already marked
`COMPLETED`).

Expected:
- `GoalAgent.dependency_status()` resolves the dependency ids into full `Goal`
  objects and correctly reports `all_dependencies_complete`

## Example 3 — Conflict detection requires a judgment call, not a rule

Input:
Two goals both requiring weekend time ("weekend interview prep" and "weekend
Kubernetes course").

Expected:
- `detect_conflict()` uses the LLM specifically because "do these goals
  compete for the same time/resources" is a judgment call, not something
  deterministic code can decide — raises `ValueError` if no LLM was configured,
  rather than silently skipping the check

## Example 4 — Priority ranking and neglect detection are deterministic

Input:
Multiple goals with different priorities and deadlines; one goal untouched
for 40 days.

Expected:
- `recommend_priorities()` ranks by priority first, then deadline proximity —
  a sortable, auditable ranking, not an LLM call (unlike conflict detection,
  this doesn't need judgment)
- `neglected_goals()` flags the stale, still-active goal using a plain
  age-since-`updated_at` check — Section 34's "surface neglected goals," made
  concrete and inspectable

## Example 5 — Weekly review never fabricates accomplishments

Input:
`WeeklyReviewSources` populated only with GitHub activity (all other sources
default to "no data" placeholders).

Expected:
- `generate_weekly_review()` returns Section 35's exact 7-section structure
  (what happened, accomplishments, changes, behind, requires attention,
  decisions made, next week)
- The prompt explicitly forbids inventing accomplishments/decisions not
  present in the given sources — the same fabrication discipline
  (Section 38) applied across all domains at once, not just within one

## Example 6 — Daily brief is structurally advisory-only

Input:
Commitments, blockers, and tasks.

Expected:
- `generate_daily_brief()` returns a plain ordered list of priorities
- `DailyBrief` has no `approved`/`executed` field at all — Section 36:
  "This should remain advisory until Phase 4." There is nothing on this model
  a caller could misuse as an authorization to act.

## Example 7 — Cross-domain recommendation (Section 31's Kubernetes example)

Input:
"Should I learn Kubernetes?" with pre-computed perspectives from LEARNING,
CAREER, and PM.

Expected:
- `combine_domain_perspectives()` reproduces Section 31's exact worked example
  shape: career relevance, current-work relevance, learning difficulty,
  recommended priority, plus reasoning
- It never regenerates domain-specific content itself — it only combines
  perspectives already produced by each domain's own agent, so each domain's
  factuality/grounding guarantees (Career OS's grounded suggestions, Learning
  OS's factual/analogy tagging) carry through untouched

## Example 8 — Cross-domain evaluation (Section 37)

Input:
A recommendation and the perspectives it was built from.

Expected:
- `check_correct_domain_selection()` verifies the router chose exactly the
  expected domain set for a labeled cross-domain case
- `check_all_expected_perspectives_present()` verifies no relevant domain's
  perspective was silently dropped
- `check_reasoning_references_perspectives()` is a cheap, auditable proxy for
  "reasoning consistency" — the recommendation's reasoning must actually
  reference content from the given perspectives, not read as boilerplate that
  ignored them entirely

## Non-goals for this milestone

- The Weekly Review / Daily Brief modules take pre-collected source strings
  rather than reaching into GitHub/Calendar/Memory themselves — an
  orchestration layer that actually calls Phase 2's integrations and Phase 3's
  domain agents to build those source strings is natural follow-up wiring,
  not built in this pass, so each piece stays independently testable with
  plain strings.
