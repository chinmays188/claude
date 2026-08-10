# Agent Guardrails

## Example 1 — Normal completion within budget

Input:
"What is 47 * 12?" (default budget: max_turns=8, max_tool_calls=6, timeout=30s)

Expected:
- Agent completes in 1-2 turns
- `stop_reason == "task_completed"`
- No budget errors

## Example 2 — Runaway tool-calling loop (Section 15 "infinite planning")

Condition:
LLM always responds with `{"action": "call_tool", ...}` and never emits `final_answer`,
budget set to `max_turns=3`.

Expected:
- Loop halts after 3 turns, not before, not after
- `stop_reason == "max_turns_reached"`
- Response communicates the answer may be incomplete (Section 38 degraded mode) —
  never silently returns as if the task fully succeeded

## Example 3 — Tool-call budget reached before turn budget

Condition:
`max_tool_calls=2`, `max_turns=100`, LLM always requests a tool call.

Expected:
- Loop halts after exactly 2 tool calls
- `stop_reason == "max_tool_calls_reached"`

## Example 4 — Timeout

Condition:
`timeout_seconds` set very low; agent loop takes longer.

Expected:
- Loop halts on the next budget check after the timeout elapses
- `stop_reason == "timeout"`

## Example 5 — Hallucinated tool inside a loop

Condition:
LLM repeatedly requests a tool name not in the registry.

Expected:
- Each hallucinated request does NOT count as a tool call (no unauthorized execution)
- Each attempt still counts as a turn (Section 60: max turns is a stop condition
  independent of whether real work happened)
- Loop eventually halts via `max_turns_reached`, not an infinite loop

## Non-goal for this milestone

- Human escalation (Section 61) is not implemented — degraded response text is
  the only recovery path built here. Escalation UX is deferred.
