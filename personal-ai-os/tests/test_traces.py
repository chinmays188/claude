import time

from app.observability.traces import TraceRecorder


def test_trace_has_execution_and_session_ids():
    recorder = TraceRecorder(session_id="s1", user_id="u1")

    trace = recorder.finish()

    assert trace.session_id == "s1"
    assert trace.user_id == "u1"
    assert trace.execution_id  # auto-generated, non-empty


def test_span_records_duration():
    recorder = TraceRecorder(session_id="s1", user_id="u1")

    with recorder.span("llm_call", kind="llm"):
        time.sleep(0.01)

    trace = recorder.finish()

    assert len(trace.spans) == 1
    assert trace.spans[0].duration_ms > 0


def test_nested_spans_form_parent_child_hierarchy():
    recorder = TraceRecorder(session_id="s1", user_id="u1")

    with recorder.span("agent_run", kind="agent"):
        with recorder.span("tool_call", kind="tool"):
            pass

    trace = recorder.finish()

    assert len(trace.spans) == 1
    assert trace.spans[0].name == "agent_run"
    assert len(trace.spans[0].children) == 1
    assert trace.spans[0].children[0].name == "tool_call"


def test_tool_and_retrieval_spans_increment_trace_counters():
    recorder = TraceRecorder(session_id="s1", user_id="u1")

    with recorder.span("t1", kind="tool"):
        pass
    with recorder.span("t2", kind="tool"):
        pass
    with recorder.span("r1", kind="retrieval"):
        pass

    trace = recorder.finish()

    assert trace.tool_calls == 2
    assert trace.retrieval_calls == 1


def test_span_error_is_captured_and_reraised():
    recorder = TraceRecorder(session_id="s1", user_id="u1")

    try:
        with recorder.span("failing", kind="tool"):
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    trace = recorder.finish(status="error")

    assert trace.status == "error"
    assert trace.spans[0].status == "error"
    assert trace.spans[0].error == "boom"


def test_finish_records_total_latency():
    recorder = TraceRecorder(session_id="s1", user_id="u1")
    time.sleep(0.01)

    trace = recorder.finish()

    assert trace.latency_ms > 0


def test_span_metadata_is_stored():
    recorder = TraceRecorder(session_id="s1", user_id="u1")

    with recorder.span("llm_call", kind="llm", model="gemini-3.5-flash-lite"):
        pass

    trace = recorder.finish()

    assert trace.spans[0].metadata["model"] == "gemini-3.5-flash-lite"
