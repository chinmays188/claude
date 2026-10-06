from app.observability.latency_breakdown import compute_latency_breakdown
from app.observability.traces import Span, Trace


def _span(name: str, kind: str, duration_ms: float, children: list[Span] | None = None) -> Span:
    started = 0.0
    return Span(
        name=name, kind=kind, started_at=started, ended_at=started + duration_ms / 1000,
        children=children or [],
    )


def test_aggregates_duration_by_kind():
    trace = Trace(
        session_id="s", user_id="u", latency_ms=300.0,
        spans=[_span("routing", "classification", 50.0), _span("agent", "agent", 200.0)],
    )

    breakdown = compute_latency_breakdown(trace)

    assert breakdown.by_kind_ms == {"classification": 50.0, "agent": 200.0}
    assert breakdown.total_span_ms == 250.0
    assert breakdown.unaccounted_ms == 50.0


def test_flattens_nested_spans_without_double_counting_parent():
    tool_span = _span("tool:calculator", "tool", 30.0)
    agent_span = _span("agent_run", "agent", 100.0, children=[tool_span])
    trace = Trace(session_id="s", user_id="u", latency_ms=100.0, spans=[agent_span])

    breakdown = compute_latency_breakdown(trace)

    assert breakdown.by_kind_ms == {"agent": 100.0, "tool": 30.0}
    assert breakdown.total_span_ms == 130.0


def test_ignores_spans_with_no_duration():
    unfinished = Span(name="pending", kind="tool", started_at=0.0)
    trace = Trace(session_id="s", user_id="u", latency_ms=10.0, spans=[unfinished])

    breakdown = compute_latency_breakdown(trace)

    assert breakdown.by_kind_ms == {}
    assert breakdown.total_span_ms == 0.0


def test_share_by_kind_sums_to_one():
    trace = Trace(
        session_id="s", user_id="u", latency_ms=100.0,
        spans=[_span("a", "agent", 25.0), _span("b", "tool", 75.0)],
    )

    breakdown = compute_latency_breakdown(trace)
    shares = breakdown.share_by_kind()

    assert shares == {"agent": 0.25, "tool": 0.75}


def test_share_by_kind_empty_when_no_spans_have_duration():
    trace = Trace(session_id="s", user_id="u", latency_ms=10.0, spans=[])

    breakdown = compute_latency_breakdown(trace)

    assert breakdown.share_by_kind() == {}


def test_unaccounted_ms_never_negative():
    trace = Trace(session_id="s", user_id="u", latency_ms=10.0, spans=[_span("a", "agent", 1000.0)])

    breakdown = compute_latency_breakdown(trace)

    assert breakdown.unaccounted_ms == 0.0
