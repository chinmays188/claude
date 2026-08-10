# Model Adaptation

## Example 1 — Fresh external knowledge recommends RAG

Input:
`AdaptationProblem(needs_fresh_external_knowledge=True)`

Expected:
- `recommend_approach()` returns `RAG` (Section 57: "the model doesn't know my
  latest project documentation" -> RAG)

## Example 2 — Specific output style recommends fine-tuning

Input:
`AdaptationProblem(needs_specific_output_style_or_format=True)`

Expected:
- Returns `FINE_TUNING` (Section 57: consistently fails to follow output style
  despite examples -> investigate fine-tuning)

## Example 3 — Simple, example-solvable task recommends ICL

Input:
`AdaptationProblem(is_simple_and_example_solvable=True)`

Expected:
- Returns `IN_CONTEXT_LEARNING`

## Example 4 — Smaller model reproducing larger model's behavior recommends distillation

Input:
`AdaptationProblem(needs_smaller_model_to_match_larger_model=True)`

Expected:
- Returns `DISTILLATION`

## Example 5 — No signal set

Input:
An `AdaptationProblem` with all flags false.

Expected:
- Raises `ValueError` rather than guessing an approach — an undiagnosed problem
  should not silently default to any one adaptation strategy

## Real experiment: `experiments/model_adaptation/README.md`

Documents a concrete sample task (answering questions about this project's own
spec doc), compares all four approaches against it (cost, latency, quality,
maintenance, freshness, data requirement, failure modes per Section 56), and
states the verdict (RAG) plus — the actual point of Section 56/57 — explicitly
documents when each of the other three approaches would be the *wrong* choice
for this and adjacent tasks.

## Non-goal for this milestone

- Fine-tuning and distillation are not implemented (no training infrastructure
  in this project). Per Section 56: "The objective is not to implement all four
  immediately... the objective is to understand when is each approach the wrong
  tool" — that understanding is captured in the experiment README and the
  `recommend_approach()` decision rules, not in trained models.
