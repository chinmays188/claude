# Phase 3 Remaining Pieces (Sections 38-42, 47-51)

## Example 1 — Consolidated guardrails registry traces to real enforcement

Input:
`DOMAIN_GUARDRAILS` (`app/domains/guardrails.py`).

Expected:
- Every entry's `enforced_by` path resolves to a real module/function/class —
  verified by a test that actually imports each path, so the registry can't
  silently drift from the code it claims to document
- All 4 domains (CAREER/PM/FINANCE/LEARNING) are represented, matching
  Section 38's per-domain rule list exactly
- No new enforcement logic lives here — every rule is already structurally
  enforced inside its own domain (grounding checks, tagging requirements,
  raised exceptions); this is a pointer registry, not a second copy of the logic

## Example 2 — Domain golden sets are loadable and countable

Input:
`evals/{career,pm,finance,learning,cross_domain}/*.json`.

Expected:
- `load_domain_cases()` loads every case file in a domain's directory
- `count_cases_by_domain()` reports current case counts per domain — Section
  39's "50 cases / domain, eventually 100+" target is now a queryable number,
  not just an aspiration in prose

## Example 3 — Domain cost attribution extends Phase 1's CostTracker, doesn't replace it

Input:
A `JourneyCost` (Phase 1, Milestone 13) with entries for a career workflow and
a shared component (the domain router).

Expected:
- `attribute_journey_cost_to_domains()` tags each entry with a domain via a
  caller-supplied component->domain map
- An entry for a component not in the map (e.g. shared infra like the domain
  router) is attributed to `"(none)"` — Section 40's point that shared AI
  infrastructure costs don't belong to any single domain
- `JourneyCost`/`CostEntry` themselves are untouched — existing Phase 1/2
  callers are unaffected

## Example 4 — Journey tracing reuses Phase 1's TraceRecorder as-is

Input:
A domain request's span hierarchy: domain_router -> career_agent ->
resume_retrieval (nested) -> llm_call (nested).

Expected:
- `new_domain_journey()` returns a plain `TraceRecorder` (Phase 1, Milestone
  12) — no new Trace/Span schema introduced
- `journey_id()` is Section 41's "journey_123" concept, made explicit as an
  accessor rather than requiring callers to know `execution_id` is the same
  field

## Example 5 — Domain dashboards match Sections 48-51's exact field lists

Input:
A `GoalStore` with goals across all 4 domains, plus caller-supplied workflow
outputs (applications count, feedback themes, portfolio value, learning progress).

Expected:
- `get_career_dashboard()` / `get_pm_dashboard()` / `get_finance_dashboard()` /
  `get_learning_dashboard()` each return exactly the fields their respective
  section lists (Career: applications/resume readiness/interview readiness/
  skill gaps/career goals; PM: feedback themes/open requests/sprint status/
  commitments/project risks; Finance: portfolio/allocation/goals/loans/risk
  indicators; Learning: subjects/progress/gaps/exercises/scores/goals)
- Goal counts per domain are pulled from the shared `GoalStore` (Sections
  33-34); everything else is caller-supplied from each domain's own workflow
  outputs — these functions only shape data, never compute or fabricate it
- All 4 default gracefully to empty/zero when no data is supplied, rather
  than raising or returning `None` everywhere

## Non-goals

- No dashboard UI is built (consistent with Phase 2 Milestone 29's scope
  decision — data layer only).
- Domain golden case *runners* with per-workflow strict assertions already
  exist as the individual test files (`test_career_jd_analysis.py`, etc.);
  `domain_golden.py`'s loader is for counting/iterating the labeled case
  files themselves, not a second, looser test framework.
