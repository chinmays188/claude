# Real-World Integrations

## Example 1 — GitHub activity summary

Input:
"What did I accomplish on this project this week?" → `GitHubActivityTool`
fetches commits/PRs/issues for a repo and date range.

Expected:
- `summarize_activity()` produces a deterministic, non-LLM-generated listing of
  what actually happened — the LLM's job downstream is to phrase it, not
  invent it (Section 23: "no fabricated activity")
- `GitHubClient` has no write methods at all — read-only by construction, not
  by convention (Section 22: "Start with read-only integrations")

## Example 2 — Correct repository / correct time period

Input:
Activity fetched for `owner/repo`, Jan 1–31.

Expected:
- `check_correct_repository()` / `check_correct_time_period()` verify the
  activity actually matches what was asked for — catches a bug where the wrong
  repo or an unintended date range silently got queried

## Example 3 — No fabricated activity

Input:
A (hypothetically LLM-generated) summary mentioning a PR number or commit sha
that was never actually in the fetched `GitHubActivity`.

Expected:
- `check_no_fabricated_activity()` flags it — every commit sha / PR number /
  issue number referenced in a summary must trace back to something the API
  actually returned

## Example 4 — Calendar conflicts

Input:
Two overlapping events on the same day.

Expected:
- `CalendarClient.find_conflicts()` detects the overlap
- `CalendarDayTool` reports it in plain text for the agent to relay
- `CalendarClient` has no `create_event`/`delete_event` methods — Section 24:
  "Do not initially modify calendar events. Read-only first."

## Example 5 — Email classification into Section 25's 5 categories

Input:
An email fetched via `EmailClient`.

Expected:
- `classify_email()` returns exactly one of FYI / ACTION_REQUIRED /
  WAITING_FOR_RESPONSE / COMMITMENT / URGENT — matching Section 25's category
  list precisely
- `EmailClient` has no `send_email`/`delete_email` methods — same read-only
  discipline as Calendar and GitHub

## Scope note (per project decision)

- **GitHub**: real integration, via `httpx` against the actual GitHub REST API,
  authenticated with a token the user supplies. Tested offline using
  `httpx.MockTransport` (no real network calls in the test suite).
- **Calendar / Email**: stub clients with the identical read-only interface a
  real Google Calendar / Gmail integration would expose, backed by
  caller-supplied fixed data rather than OAuth — no credentials/setup required
  to use or test them. Swapping in a real backend later means implementing the
  same `get_events`/`get_emails` methods against a real API, not changing any
  calling code.
- Slack/Teams (Section 22's 5th integration) is not implemented in this
  milestone.

## Every integration is a Phase 1 `Tool`

`GitHubActivityTool`, `CalendarDayTool`, and `EmailSummaryTool` all extend
Phase 1's `Tool` base class (Milestone 3) — they slot directly into the
existing `ToolRegistry`/`ToolAgent` tool-calling loop, argument validation, and
budget-bounded execution, rather than introducing a parallel integration
framework.
