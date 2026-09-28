from app.observability.error_analysis import (
    failure_examples,
    span_failure_counts_by_kind,
    stop_reason_counts,
    trace_error_rate,
)
from app.observability.traces import Span, Trace


def _span(name, kind, status="success", error=None, metadata=None, children=None):
    return Span(
        name=name, kind=kind, started_at=0.0, ended_at=1.0,
        status=status, error=error, metadata=metadata or {}, children=children or [],
    )


def _trace(status="success", spans=None):
    return Trace(session_id="s", user_id="u", status=status, spans=spans or [])


def test_trace_error_rate_empty_is_real_zero():
    assert trace_error_rate([]) == 0.0


def test_trace_error_rate_computes_real_fraction():
    traces = [_trace("success"), _trace("error"), _trace("success"), _trace("error")]
    assert trace_error_rate(traces) == 0.5


def test_span_failure_counts_by_kind_flattens_nested_spans():
    child = _span("tool:calculator", "tool", status="error", error="division by zero")
    parent = _span("orchestrator_run", "agent", children=[child])
    traces = [_trace(spans=[parent])]

    counts = span_failure_counts_by_kind(traces)

    assert counts == {"tool": 1}


def test_span_failure_counts_ignores_successful_spans():
    parent = _span("orchestrator_run", "agent", children=[_span("tool:calculator", "tool")])
    traces = [_trace(spans=[parent])]

    assert span_failure_counts_by_kind(traces) == {}


def test_failure_examples_include_real_trace_id_and_error():
    child = _span("tool:calculator", "tool", status="error", error="Could not evaluate '1/0'")
    parent = _span("orchestrator_run", "agent", children=[child])
    trace = _trace(spans=[parent])
    trace.execution_id = "abc123"

    examples = failure_examples([trace])

    assert examples["tool"][0]["trace_id"] == "abc123"
    assert examples["tool"][0]["error"] == "Could not evaluate '1/0'"
    assert examples["tool"][0]["span_name"] == "tool:calculator"


def test_failure_examples_caps_per_kind():
    spans = [_span(f"tool:calc{i}", "tool", status="error", error="e") for i in range(5)]
    trace = _trace(spans=spans)

    examples = failure_examples([trace], limit_per_kind=2)

    assert len(examples["tool"]) == 2


def test_stop_reason_counts_reads_span_metadata():
    span = _span("orchestrator_run", "agent", metadata={"stop_reason": "max_tool_calls_reached"})
    traces = [_trace(spans=[span]), _trace(spans=[span])]

    assert stop_reason_counts(traces) == {"max_tool_calls_reached": 2}


def test_stop_reason_counts_omits_traces_without_it():
    traces = [_trace(spans=[_span("orchestrator_run", "agent")])]

    assert stop_reason_counts(traces) == {}
