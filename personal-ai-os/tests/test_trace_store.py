import sqlite3

import pytest

from app.observability.traces import TraceRecorder
from app.observability.trace_store import TraceNotFoundError, TraceStore


@pytest.fixture
def store():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return TraceStore(conn)


def _sample_trace(session_id="s1", user_id="u1"):
    recorder = TraceRecorder(session_id=session_id, user_id=user_id)
    with recorder.span("router", kind="classification"):
        pass
    return recorder.finish()


def test_save_and_get_roundtrips_full_trace(store):
    trace = _sample_trace()

    store.save(trace, input_text="What is my finance goal progress?")
    loaded = store.get(trace.execution_id)

    assert loaded.execution_id == trace.execution_id
    assert loaded.session_id == "s1"
    assert len(loaded.spans) == 1
    assert loaded.spans[0].name == "router"


def test_get_missing_trace_raises(store):
    with pytest.raises(TraceNotFoundError):
        store.get("does-not-exist")


def test_list_summaries_orders_newest_first(store):
    t1 = _sample_trace(session_id="s1")
    store.save(t1, input_text="first request")
    t2 = _sample_trace(session_id="s2")
    store.save(t2, input_text="second request")

    summaries = store.list_summaries()

    assert [s["execution_id"] for s in summaries] == [t2.execution_id, t1.execution_id]
    assert summaries[0]["input_text"] == "second request"


def test_save_is_idempotent_on_same_execution_id(store):
    trace = _sample_trace()
    store.save(trace, input_text="v1")
    store.save(trace, input_text="v2")  # re-save same execution_id

    summaries = store.list_summaries()

    assert len(summaries) == 1
    assert summaries[0]["input_text"] == "v2"
