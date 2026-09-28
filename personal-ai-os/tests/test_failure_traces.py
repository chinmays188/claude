import sqlite3

from app.dashboard_ui.failure_traces import load_failure_trace_records, seed_failure_traces
from app.observability.trace_store import TraceStore


def _find_span(spans, predicate):
    for span in spans:
        if predicate(span):
            return span
        found = _find_span(span.children, predicate)
        if found:
            return found
    return None


def test_seed_failure_traces_populates_store_without_gemini_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = TraceStore(conn)

    count = seed_failure_traces(store)

    summaries = store.list_summaries()
    assert count == len(summaries)
    assert count == 3  # tool failure, retrieval failure, budget exhausted


def test_seed_failure_traces_is_idempotent():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = TraceStore(conn)

    seed_failure_traces(store)
    seed_failure_traces(store)

    execution_ids = [s["execution_id"] for s in store.list_summaries()]
    assert len(execution_ids) == len(set(execution_ids))


def test_includes_a_real_caught_tool_failure_span():
    """The tool-failure scenario must show a real failed tool span
    (status='error') while the overall trace still completes -- proving the
    ToolAgent bug fix (a tool error is caught and recovered from, not fatal)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = TraceStore(conn)
    seed_failure_traces(store)
    traces = [store.get(s["execution_id"]) for s in store.list_summaries()]

    def _is_failed_tool_span(span):
        return span.kind == "tool" and span.status == "error"

    matches = [t for t in traces if _find_span(t.spans, _is_failed_tool_span) is not None]
    assert matches
    assert any(t.status == "success" for t in matches)  # recovered, not fatal


def test_includes_a_real_span_level_retrieval_failure():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = TraceStore(conn)
    seed_failure_traces(store)
    traces = [store.get(s["execution_id"]) for s in store.list_summaries()]

    def _is_failed_retrieval_span(span):
        return span.kind == "retrieval" and span.status == "error"

    assert any(_find_span(t.spans, _is_failed_retrieval_span) is not None for t in traces)


def test_includes_a_real_budget_exhausted_trace():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = TraceStore(conn)
    seed_failure_traces(store)
    traces = [store.get(s["execution_id"]) for s in store.list_summaries()]

    def _has_budget_stop_reason(trace):
        span = _find_span(trace.spans, lambda s: s.name == "orchestrator_run")
        return span is not None and span.metadata.get("stop_reason") == "max_tool_calls_reached"

    assert any(t.status == "error" and _has_budget_stop_reason(t) for t in traces)


def test_load_failure_trace_records_returns_input_text_and_trace_json():
    records = load_failure_trace_records()
    assert len(records) == 3
    for record in records:
        assert "input_text" in record
        assert "trace_json" in record
