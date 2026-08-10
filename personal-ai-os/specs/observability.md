# Observability

## Example 1 — Trace records execution identity

Input:
A `TraceRecorder` created for a session/user.

Expected:
- `Trace.execution_id` is auto-generated and unique per run
- `session_id`/`user_id` are preserved, matching Section 47's schema

## Example 2 — Nested spans mirror the real execution hierarchy

Input:
An agent span containing a nested tool-call span (Section 46: agent span
contains LLM/tool/retrieval spans).

Expected:
- The tool span appears as a child of the agent span, not a sibling
- Each span records its own duration independently

## Example 3 — Tool/retrieval counts roll up to the trace

Input:
2 tool spans and 1 retrieval span recorded during one execution.

Expected:
- `Trace.tool_calls == 2`, `Trace.retrieval_calls == 1` — matching Section 47's
  flat trace-level counters, without requiring the caller to count spans manually

## Example 4 — Span errors are captured, not swallowed

Input:
An exception raised inside a `with recorder.span(...)` block.

Expected:
- The span's `status` becomes `"error"` and `error` captures the message
- The exception still propagates to the caller — a span never silently absorbs
  a real failure

## Non-goal for this milestone

- No persistence layer (SQLite) is wired up yet — `Trace`/`Span` are in-memory
  Pydantic models, ready to be serialized to `data/personal_ai.db` in a follow-up.
  No external tracing backend (OpenTelemetry, etc.) is integrated — this is a
  lightweight recorder matching the spec's own schema, not a vendor integration.
