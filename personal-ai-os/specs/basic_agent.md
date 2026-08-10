# Basic Agent

## Example 1 — Normal input

Input:
"Explain RAG."

Expected:
- Agent calls `llm.generate()` (not the provider SDK directly)
- Response validates against `AgentResponse` schema: `input`, `output`, `model`
- `output` is non-empty text
- `model` matches the configured Gemini model name

## Example 2 — Empty input

Input:
""

Expected:
- Agent raises a validation error before calling the LLM
- No API call is made

## Example 3 — Whitespace-only input

Input:
"   "

Expected:
- Treated the same as empty input
- Agent raises a validation error before calling the LLM

## Example 4 — Long input

Input:
A ~5,000 word block of text.

Expected:
- Agent does not crash
- Request is sent to the provider as-is (no chunking/compression yet — that's Milestone 10)
- Response still validates against `AgentResponse` schema

## Failure case — Provider unavailable

Condition:
Gemini API key missing or provider raises an exception.

Expected:
- Error propagates clearly (no silent empty response)
- No fallback yet (fallback chains are Milestone 4/36) — this milestone only requires the failure to be visible, not recovered from
