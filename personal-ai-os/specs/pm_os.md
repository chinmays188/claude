# PM OS

## Example 1 — Feedback intelligence clusters real feedback into themes

Input:
Raw feedback: "My refund is taking forever." / "Refunds are too slow."

Expected:
- `analyze_feedback()` returns Section 15's exact output shape: top themes
  (with frequency/severity/impact/trend), emerging/declining themes, critical
  issues, recommended actions
- `check_feedback_themes_grounded()` verifies each theme actually traces back
  to word overlap with the raw feedback — catches a theme like "pricing
  complaints" appearing in the output when nothing in the raw feedback
  mentioned pricing (Section 38: never fabricate customer data)

## Example 2 — Stakeholder request analysis explains its recommendation

Input:
"Can we add automated refunds?" against a retrieved roadmap excerpt already
planning refund automation.

Expected:
- Returns one of Section 16's exact 5 recommendations (BUILD/INVESTIGATE/
  REJECT/DEFER/NEED_MORE_EVIDENCE)
- `reasoning` is always populated — Section 16: "The system should explain why"
- With no retrieved evidence at all, the LLM is told explicitly that no
  evidence was found (not silently given an empty string), which naturally
  steers toward `NEED_MORE_EVIDENCE` rather than a confident guess

## Example 3 — PRD generation is never accepted without a Critic pass

Input:
A product idea ("Automate refunds").

Expected:
- `draft_prd()` produces Section 17's pipeline output (problem/context/
  hypothesis/solution/metrics/experiment)
- `critique_prd()` (the Critic Agent) answers all 6 of Section 17's explicit
  challenge questions, plus a verdict (proceed/revise/reject)
- `check_critic_challenged_the_prd()` flags a critique whose answers are all
  trivially short/non-committal ("yes", "ok", "fine") — a Critic that doesn't
  actually challenge anything has failed its one job
- `draft_and_critique_prd()` is the recommended entry point — a PRD without
  its critique is treated as an incomplete artifact, not an optional add-on

## Example 4 — Sprint planning prioritizes across all 4 input sources

Input:
Stakeholder requests, backlog, bug reports, and commitments.

Expected:
- `create_sprint_plan()` returns Section 18's exact output shape (prioritized
  work with source/priority/owner/dependencies/risk, overall risks, suggested
  scope)
- The sprint planner module has no Jira-write function at all — Section 18:
  "The system should NOT automatically change Jira/project management tools
  without approval." Any real write to an external PM tool must go through
  Phase 2's `PolicyEngine` as an ACT-class action, exactly like Milestone 25's
  `send_email`/`create_calendar_event` — this module only ever produces a plan.

## Data note

All test fixtures are fabricated example feedback/requests/PRDs — no real
customer, stakeholder, or product data, consistent with the project's
synthetic-data-only approach for domain-specific milestones.

## Non-goals for this milestone

- `collect_feedback`, `cluster_feedback`, `detect_trends`,
  `extract_product_requests`, `prioritize_requests`, `create_experiment`,
  `define_metrics`, `summarize_project`, `identify_blockers`,
  `generate_stakeholder_update`, `track_commitments` (the remaining Section 14
  skills) are not each built as standalone functions — `analyze_feedback()`
  already covers clustering/trend-detection/theming as one pipeline; a
  dedicated project-summary/commitment-tracking module is natural follow-up
  work reusing Phase 2's `TaskStore`/`GraphStore` rather than new
  infrastructure.
