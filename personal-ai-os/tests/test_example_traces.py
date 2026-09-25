import sqlite3

from app.dashboard_ui.example_traces import seed_example_traces
from app.observability.trace_store import TraceStore


def test_seed_example_traces_populates_store_without_gemini_key(monkeypatch):
    """The whole point of committing these as fixed examples is that the
    public Streamlit Cloud deployment (no GEMINI_API_KEY configured) can
    still show real trace content -- confirm seeding needs no key at all."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = TraceStore(conn)

    count = seed_example_traces(store)

    summaries = store.list_summaries()
    assert count == len(summaries)
    assert count >= 5  # at least the 5 known examples covering different domains/outcomes


def test_seed_example_traces_is_idempotent():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = TraceStore(conn)

    seed_example_traces(store)
    seed_example_traces(store)  # re-seed

    summaries = store.list_summaries()
    execution_ids = [s["execution_id"] for s in summaries]
    assert len(execution_ids) == len(set(execution_ids))  # no duplicates


def test_seed_example_traces_includes_a_real_tool_call():
    """At least one example must show a real tool-call span, since that's
    part of what this page exists to demonstrate."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = TraceStore(conn)
    seed_example_traces(store)

    summaries = store.list_summaries()
    traces = [store.get(s["execution_id"]) for s in summaries]

    assert any(t.tool_calls > 0 for t in traces)


def _find_span(spans, name):
    for span in spans:
        if span.name == name:
            return span
        found = _find_span(span.children, name)
        if found:
            return found
    return None


def test_seed_example_traces_includes_a_general_domain_example():
    """At least one example must show UnifiedRouter classifying GENERAL
    (no Phase 3 domain fits) -- a real, distinct, first-class outcome worth
    demonstrating, not an error case."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = TraceStore(conn)
    seed_example_traces(store)

    summaries = store.list_summaries()
    traces = [store.get(s["execution_id"]) for s in summaries]

    def _has_general_domain(trace):
        span = _find_span(trace.spans, "unified_routing")
        return span is not None and span.metadata.get("domain") == "GENERAL"

    assert any(_has_general_domain(t) for t in traces)


def test_seed_example_traces_includes_all_three_task_types():
    """The 5 examples should collectively exercise research, analysis, and
    planning -- all 3 agents UnifiedRouter/Orchestrator can dispatch to."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = TraceStore(conn)
    seed_example_traces(store)

    summaries = store.list_summaries()
    traces = [store.get(s["execution_id"]) for s in summaries]

    agents_seen = set()
    for t in traces:
        run_span = _find_span(t.spans, "orchestrator_run")
        if run_span and run_span.metadata.get("agent"):
            agents_seen.add(run_span.metadata["agent"])

    assert agents_seen == {"research_agent", "analyst_agent", "planner_agent"}


def test_seed_example_traces_includes_memory_lookup_span():
    """Every example (post the memory-instrumentation change) should record
    a memory_lookup span, even when it finds nothing relevant."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = TraceStore(conn)
    seed_example_traces(store)

    summaries = store.list_summaries()
    traces = [store.get(s["execution_id"]) for s in summaries]

    assert all(any(span.name == "memory_lookup" for span in t.spans) for t in traces)
