# Career OS

## Example 1 — JD analysis pipeline

Input:
A job description for a "Senior AI PM" role.

Expected:
- `parse_jd()` extracts structured requirements (role, required/preferred
  skills, responsibilities, seniority) — Section 9's "JD Parser -> Requirements
  extraction -> Skill mapping" stages
- `analyze_jd()` retrieves the candidate's real resume/achievement excerpts via
  `SecureRetriever` (Milestone 19's access-control guarantee applies here too),
  then produces Section 9's exact output fields: overall/technical/ai/pm/
  domain/leadership fit, major gaps, recommended resume changes, interview risks

## Example 2 — JD analysis with no resume on file

Input:
A candidate with zero ingested documents.

Expected:
- The pipeline still runs (doesn't crash on empty retrieval) — the LLM sees an
  explicit "(no resume or achievement documents found)" placeholder rather than
  an empty string that could be misread as "documents exist but say nothing"

## Example 3 — Resume optimization never invents achievements

Input:
A JD and the candidate's real achievement excerpts.

Expected:
- `optimize_resume()` returns suggestions each tagged with a
  `grounding_achievement_ids` — an excerpt id the suggestion is based on
- `check_resume_suggestions_grounded()` / `check_outcome_grounded()` verify
  every cited id actually came from the excerpts the model was given — a
  fabricated id fails the check, directly enforcing Section 10 rule 6 ("Never
  invent achievements")

## Example 4 — Interview story built from a real experience

Input:
"Give me a conflict-management story."

Expected:
- `build_interview_story()` retrieves relevant real experiences, then builds a
  STAR-structured (`situation/task/action/result`) answer
- `source_achievement_id` must match one of the actually-retrieved excerpt ids;
  if the model cites an id that wasn't retrieved, `NoRelevantExperienceError`
  is raised — the story is treated as likely fabricated rather than accepted
- `check_star_completeness()` verifies all four STAR fields are non-empty
  (Section 11's "STAR completeness" evaluation criterion)

## Example 5 — No relevant experience exists at all

Input:
A request with zero matching retrieved documents.

Expected:
- `NoRelevantExperienceError` raised immediately — the system never fabricates
  a story when it has nothing real to build one from

## Example 6 — Access control holds inside Career OS too

Input:
A resume optimization request where the requester doesn't own the retrieved
documents.

Expected:
- `SecureRetriever` (Milestone 19) returns nothing for documents the requester
  doesn't own — Career OS inherits this guarantee automatically since it never
  bypasses `SecureRetriever` for its own retrieval

## Data note

All test fixtures (`tests/fakes/example_resume.py`) are fabricated, synthetic
achievement text — not any real person's resume or career history, per project
scope decision for this milestone.

## Non-goals for this milestone

- `generate_resume_bullets`, `analyze_company`, `draft_networking_message`
  (Section 8's skill list) are not implemented in this pass — JD analysis,
  resume optimization, and interview story building are the three workflows
  Sections 9-11 spell out in full pipeline detail; the remaining skills are
  smaller, similar-shaped extensions of the same retrieval-then-generate
  pattern, left for follow-up.
- ATS compatibility scoring (mentioned in Section 10's evaluation checklist) is
  not separately implemented — `major_gaps`/`missing_keywords` are the closest
  proxies here; a dedicated ATS-format checker would need real ATS parsing
  rules, which are out of scope for this pass.
