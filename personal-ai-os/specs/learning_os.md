# Learning OS

## Example 1 — Content is tagged factual/analogy/speculation

Input:
`explain_concept("Docker")`, `generate_analogy("Docker")`, `generate_example("Docker")`.

Expected:
- Each returns an `Explanation` tagged `kind=FACTUAL`, `ANALOGY`, or `FACTUAL`
  respectively — matching Section 38's explicit requirement that Learning OS
  "clearly distinguish factual explanation, analogy, speculation." An analogy
  is never silently presented as a literal technical claim.

## Example 2 — Exercises require application, not recall

Input:
`generate_exercise("Docker")`.

Expected:
- Returns a question plus an `expected_answer_summary` used for grading —
  the summary exists specifically so evaluation (Example 3) has a concrete
  target to check the learner's answer against, not a vague "was it good"

## Example 3 — Answer evaluation scores 5 independent dimensions

Input:
A learner's answer to an exercise.

Expected:
- `evaluate_answer()` returns Section 30's exact 5 dimensions (conceptual
  understanding, technical depth, application, system thinking, PM
  translation), each 0-10 — never a single blended score
- `check_evaluation_scores_in_range()` verifies all 5 stay within the valid
  0-10 range

## Example 4 — Knowledge gaps drive the next exercise

Input:
A weak answer revealing a specific gap (e.g. "confused Docker networking
ports"), followed by a request for the next exercise.

Expected:
- `identify_knowledge_gap()` returns the specific gap with a severity score
- `AdaptiveLoop.next_exercise()` targets the highest-severity gap's concept
  specifically, not the original concept in general — Section 29's "the
  system should adapt based on performance," made concrete

## Example 5 — Mastery requires sustained performance, not a lucky answer

Input:
One high-scoring attempt, then a second high-scoring attempt on the same
concept.

Expected:
- After 1 attempt, `mastered == False` even with a high score — a single
  attempt is not proof of mastery
- After 2 attempts both averaging >= 8/10, `mastered == True`
- This threshold logic (`MASTERY_MIN_ATTEMPTS`, `MASTERY_THRESHOLD` in
  `adaptive_loop.py`) is explicit and adjustable, not implicit in a prompt

## Example 6 — Full adaptive loop (Section 29)

Input:
A concept with no exercise supplied.

Expected:
- `AdaptiveLoop.run_round()` generates an exercise itself, evaluates the
  answer, identifies gaps, and updates `LearningProgress` in place — Section
  29's full "Concept -> Explanation -> Example -> Exercise -> Answer ->
  Evaluation -> Gap -> Next exercise" loop, minus the explanation/example step
  (generated once via `tutor.py`, not repeated every round)

## Non-goals for this milestone

- `create_learning_plan` and `track_progress` (Section 28's remaining skills)
  are partially covered by `LearningProgress`/`AdaptiveLoop.progress_for()` —
  a dedicated multi-concept learning plan generator (sequencing several
  concepts, not just tracking one) is not built in this pass.
- `generate_interview_question` (also in Section 28's list) overlaps with
  Career OS's `build_interview_story` — not duplicated here; a
  technical-interview-question variant would be a thin, separate addition.
