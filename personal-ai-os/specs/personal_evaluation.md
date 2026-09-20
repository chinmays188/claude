# Personal OS Evaluation

## Example 1 — Golden case scoped to a personal-workload category

Input:
A `career` category case: "Where did I work?" against an ingested resume,
expecting "Acme Corp" in the answer and a citation from the resume document.

Expected:
- `run_personal_golden_case()` runs the question through `PersonalRagPipeline`
  (Milestone 21), not the generic `Orchestrator` — personal workload cases test
  the personalized path specifically
- Fails with a clear reason if expected content or expected citations are
  missing — same "always explain why" discipline as Phase 1's `golden.py`

## Example 2 — Per-category pass rates, not one blended number

Input:
A mix of career, learning, PM, and personal-knowledge cases, some passing,
some failing.

Expected:
- `pass_rate_by_category()` reports each of Section 34's four categories
  independently — a single overall pass rate could hide "career eval is
  badly broken but everything else is fine"

## Example 3 — Actionability and trustworthiness scoring

Input:
An agent response to "what should I focus on today?"

Expected:
- `score_actionability_and_trust()` (LLM-as-judge, reusing the
  `RepairableGenerator` pattern from Milestone 4/11) scores both dimensions
  from Section 35 independently — a vague, non-actionable answer and an
  overconfident, ungrounded answer are different failure modes and should be
  visible as different numbers

## Example 4 — Human evaluation shows the full picture

Input:
A case being reviewed by a human evaluator.

Expected:
- `PersonalEvalDisplay` carries everything Section 36 requires shown:
  user request, retrieved memory, retrieved documents, agent response,
  citations, execution trace — not just the final answer in isolation

## Example 5 — Human rating uses Section 36's exact 5 fields

Input:
A human evaluator scoring a response.

Expected:
- `PersonalHumanRating` has exactly `correctness, personalization, trust,
  usefulness, citations` (1-5 each) — distinct from Phase 1's `HumanRating`
  (Milestone 11), which uses a different 6-field set without personalization

## Relationship to Phase 1

- Regression testing (Section 39's checklist item) and judge/human correlation
  are NOT reimplemented — `app/evaluation/regression.py` and
  `judge_human_correlation()` (Milestone 11) are reused as-is; they were
  already generic enough to apply to personal workloads without modification.
- Memory precision/recall, personalization score, and temporal correctness
  (3 of Section 35's 6 new metrics) were already built in Milestone 21 —
  this milestone adds the remaining two (actionability, trustworthiness) and
  the golden-set/human-eval scaffolding around all of them.
