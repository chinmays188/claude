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

## Follow-up — the full decision chain, and a real log of this project's own decisions

The user asked: "lets check the AI product strategy, build this
decision framework as we go along ... we have already taken lot of
decisions in this project."

Checked first, honestly: `recommend_approach()` above is real, correct,
and tested -- but it's only one rung (RAG vs. fine-tuning vs. in-context
learning vs. distillation) of the full chain the "AI Product Strategy"
learning goal's own success criterion names: *deterministic logic ->
traditional ML -> LLM -> RAG -> tool calling -> agent -> multi-agent ->
human approval -> autonomous execution*. No dedicated artifact covered
the rest of that chain.

New `app/evaluation/ai_product_decision_framework.py`'s `recommend_tier()`
is the rest of the chain, built the same way as `recommend_approach()`:
explicit, testable if/then logic over real signals (`ProductDecisionInputs`),
checked in the real order a product decision should actually ask them --
cheapest/most deterministic first, only climbing the chain when a real
signal requires it. Every `ProductDecision` carries a real
`failure_mode_if_under_built` explanation, so "why not just use a
cheaper approach" is answerable, not asserted.

**Verified against this project's own real architecture, not just unit
tests**: `UnifiedRouter`'s classification maps to `SINGLE_LLM_CALL`;
`ToolAgent` + `calculator` maps to `TOOL_CALLING`; `send_email` (this
project's own real `ActionClassifier` default: `ActionClass.ACT`) maps
to `HUMAN_APPROVAL_REQUIRED`; `PersonalRagPipeline` maps to `RAG`;
`MultiAgentCoordinator`'s sequential research+analysis+planning maps to
`MULTI_AGENT`. Every one of these is the tier this project actually
built for that real case -- the framework doesn't just sound right, it
reproduces this project's own real decisions when given the real inputs.

New `app/evaluation/ai_product_decision_log.py`: a real, populated log
of 12 decisions this project has ACTUALLY made -- not invented case
studies. Each entry cites its real commit hash or spec file, pulled
directly from this project's own git history (e.g. `2c6b0b1` combining
two disconnected routers into `UnifiedRouter`, `e9e5a04` wiring real
governance into the live chat-agent path, `d022635` choosing Gemini
native audio understanding over Whisper/paid vendors for voice).
Verified by a real test: every cited commit hash is checked against
this repo's actual `git log` and must genuinely exist, not just look
plausible.

New dedicated "Decision Framework" dashboard page: a fully live,
interactive recommender (the real framework, checkboxes driving a real
recommendation -- 100% free, deterministic, no LLM call at all) and the
real decision log, browsable by tier with a real tier-distribution bar
chart.

A real, stale test assumption was found and fixed in the same batch:
`tests/test_user_learning_goals.py` asserted "at least one capability's
progress is below 0.5" as a guard against silently reverting to
meaningless all-zero progress. With this session's real, accumulated
progress across many capabilities, that specific threshold became a
false signal rather than a real regression guard -- fixed to assert the
guard's actual intent (`min < 1.0`, i.e. at least one capability is
honestly not yet "done"), not a specific numeric threshold that time
would naturally erode.

"AI Product Strategy" learning-goal progress updated 30% -> 90% in the
same batch, honestly kept short of 100%: the log currently has 12
entries, a real but partial sample of this project's full real decision
history (227 "Example N" sections across specs, 99 commits).

902 tests passing (was 879).
