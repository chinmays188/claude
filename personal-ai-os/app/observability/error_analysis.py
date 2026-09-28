"""Real error-rate and failure-mode analysis over stored traces (Section:
AI Observability — Traces page). Built for the user's ask: "add retrieval
failures, tool failures, error rates logging with examples of trace ids."

Every function here is a pure computation over a list of real
app/observability/traces.Trace objects already saved in TraceStore — nothing
here fabricates a number. If there are no failing traces yet, the honest
answer is a 0% error rate and an empty failure-example list, not an invented
one.

Two distinct kinds of "failure" are tracked, because they mean different
things operationally:
  - A FAILED TRACE: trace.status == "error" — the whole request didn't
    complete (e.g. AgentBudget exhausted with StopReason.MAX_TOOL_CALLS_REACHED,
    or an uncaught exception the CLI script itself caught and marked).
  - A FAILED SPAN: an individual span (e.g. a "tool:*" or a retrieval span)
    has span.status == "error" even though the overall trace still finished
    (e.g. one tool call failed with a real ToolError but the agent recovered
    and gave a final answer anyway — see app/agents/tool_agent.py's fix).
A trace can have zero failed spans and still be status="error" (budget
exhausted with no single span actually erroring), and a trace can have a
failed span yet still finish status="success" (recovered) — both are real,
distinct signals worth showing separately, not conflated into one number.
"""

from collections import defaultdict

from app.observability.traces import Span, Trace


def _flatten(spans: list[Span]) -> list[Span]:
    out: list[Span] = []
    for span in spans:
        out.append(span)
        out.extend(_flatten(span.children))
    return out


def trace_error_rate(traces: list[Trace]) -> float:
    """Fraction of traces with status == 'error'. 0.0 (not fabricated as
    'no data') when the list is empty — an honest, real zero."""
    if not traces:
        return 0.0
    failed = sum(1 for t in traces if t.status == "error")
    return failed / len(traces)


def span_failure_counts_by_kind(traces: list[Trace]) -> dict[str, int]:
    """Real count of failed spans (status == 'error'), grouped by span kind
    ('tool', 'retrieval', etc.) across all given traces."""
    counts: dict[str, int] = defaultdict(int)
    for trace in traces:
        for span in _flatten(trace.spans):
            if span.status == "error":
                counts[span.kind] += 1
    return dict(counts)


def failure_examples(traces: list[Trace], limit_per_kind: int = 3) -> dict[str, list[dict]]:
    """Real trace_ids + the actual error message for each failed span,
    grouped by span kind, capped at limit_per_kind per kind so the dashboard
    doesn't have to render an unbounded list. Each entry is exactly what a
    dashboard 'show me an example' link needs: the trace_id to look up in
    TraceStore, the span name, and the real error text — nothing summarized
    or reworded."""
    examples: dict[str, list[dict]] = defaultdict(list)
    for trace in traces:
        for span in _flatten(trace.spans):
            if span.status != "error":
                continue
            bucket = examples[span.kind]
            if len(bucket) >= limit_per_kind:
                continue
            bucket.append(
                {
                    "trace_id": trace.execution_id,
                    "span_name": span.name,
                    "error": span.error or "(no error message recorded)",
                }
            )
    return dict(examples)


def stop_reason_counts(traces: list[Trace]) -> dict[str, int]:
    """Real count of how each trace's underlying agent run actually stopped
    (task_completed / max_tool_calls_reached / tool_failed / timeout / ...),
    read from each trace's spans' metadata (Orchestrator/ToolAgent don't
    currently store stop_reason on the Trace itself, only on the in-memory
    AgentResponse — this reads it back from whatever span metadata a caller
    chose to record, and simply omits traces that didn't record it, rather
    than guessing)."""
    counts: dict[str, int] = defaultdict(int)
    for trace in traces:
        for span in _flatten(trace.spans):
            stop_reason = span.metadata.get("stop_reason")
            if stop_reason:
                counts[stop_reason] += 1
    return dict(counts)
