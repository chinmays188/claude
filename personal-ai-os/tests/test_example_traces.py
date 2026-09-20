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


def test_seed_example_traces_includes_an_unclear_routing_example():
    """At least one example must show UNCLEAR routing (no agent/tool run),
    since that's a real, distinct behavior worth demonstrating too."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = TraceStore(conn)
    seed_example_traces(store)

    summaries = store.list_summaries()
    traces = [store.get(s["execution_id"]) for s in summaries]

    assert any(len(t.spans) == 1 and t.spans[0].name == "domain_routing" for t in traces)
