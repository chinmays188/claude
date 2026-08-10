# Tool Calling

## Example 1 — Tool needed

Input:
"What is 47 * 12?"

Expected:
- LLM decision step selects the `calculator` tool with args `{"expression": "47 * 12"}`
- Tool executes and returns `564`
- Final answer incorporates the tool result
- `AgentResponse.tool_calls == ["calculator"]`

## Example 2 — No tool needed

Input:
"Explain RAG."

Expected:
- LLM decision step returns `{"tool": null}`
- No tool is executed
- `AgentResponse.tool_calls == []`

## Example 3 — Hallucinated tool call

Condition:
LLM decision step returns a tool name not in the registry (e.g. `"send_email"`).

Expected:
- `ToolRegistry` rejects the unknown tool (`UnknownToolError`)
- Agent falls back to answering without a tool, does not crash
- `AgentResponse.tool_calls == []`

## Example 4 — Invalid tool arguments

Condition:
LLM decision step returns `{"tool": "calculator", "args": {"expression": null}}`

Expected:
- `CalculatorArgs` schema validation fails
- `ArgumentValidationError` raised
- (Repair loop for this is deferred to Milestone 4 — Structured Output; for M3 the failure must be visible, not silently swallowed)

## Example 5 — Tool execution failure

Condition:
`calculator` tool called with `{"expression": "1 / 0"}`

Expected:
- Tool raises `ToolError` (division by zero)
- Error is visible, not silently absorbed into a fabricated answer

## Retry safety

- `calculator` is declared `retry_safe = True` — deterministic, no side effects, safe to retry.
- Per Section 33, side-effecting tools (not implemented in this milestone, e.g. `send_email`) must default to `retry_safe = False`.
