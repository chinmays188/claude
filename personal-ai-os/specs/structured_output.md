# Structured Output Reliability

## Example 1 — Valid output on first try

Input:
LLM returns `{"task_type": "research", "confidence": 0.9}` immediately.

Expected:
- `RepairableGenerator.generate()` validates successfully on the first attempt
- No repair prompt is sent
- Returned object matches the schema

## Example 2 — Invalid then valid (repair succeeds)

Input:
LLM returns `{"confidence": "very high"}` (invalid), then on retry returns
`{"task_type": "research", "confidence": 0.9}` (valid).

Expected:
- First response fails schema validation
- A repair prompt is sent, including the validation error and the schema
- Second response validates successfully
- Total LLM calls: 2

## Example 3 — Repair exhausted

Input:
LLM returns invalid JSON on every call (initial + all repair attempts).

Expected:
- Exactly `max_repair_attempts + 1` total LLM calls (default: 3)
- `StructuredOutputError` raised after exhausting repairs
- No silent fallback to a guessed/default value

## Example 4 — Fallback chain: primary succeeds

Input:
Primary provider returns a valid response.

Expected:
- `FallbackProvider` returns the primary's output
- `fallback_occurred == False`
- Secondary provider is never called

## Example 5 — Fallback chain: primary fails, secondary succeeds

Input:
Primary provider raises an exception; secondary provider succeeds.

Expected:
- `FallbackProvider` returns the secondary's output
- `fallback_occurred == True`
- The fact that a fallback occurred is recorded/logged, never silent (Section 36)

## Example 6 — Fallback chain: all providers fail

Input:
All providers raise exceptions.

Expected:
- `AllProvidersFailedError` raised, containing each provider's error
- No fabricated/degraded response returned silently in its place
  (a degraded-mode UX response is a caller-level decision, not this component's)
