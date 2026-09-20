from app.observability.traces import TraceRecorder
from app.platform.otel_export import InMemoryOtelExporter, to_otel_spans


def test_to_otel_spans_flattens_hierarchy_with_parent_ids():
    recorder = TraceRecorder(session_id="s1", user_id="alice")
    with recorder.span("agent_run", kind="agent"):
        with recorder.span("tool_call", kind="tool"):
            pass
    trace = recorder.finish()

    otel_spans = to_otel_spans(trace)

    assert len(otel_spans) == 2
    parent_span = next(s for s in otel_spans if s.name == "agent_run")
    child_span = next(s for s in otel_spans if s.name == "tool_call")
    assert parent_span.parent_span_id is None
    assert child_span.parent_span_id == parent_span.span_id


def test_to_otel_spans_maps_kind_to_otel_span_kind():
    recorder = TraceRecorder(session_id="s1", user_id="alice")
    with recorder.span("llm_call", kind="llm"):
        pass
    trace = recorder.finish()

    otel_spans = to_otel_spans(trace)

    assert otel_spans[0].kind == "CLIENT"


def test_to_otel_spans_converts_timestamps_to_nanoseconds():
    recorder = TraceRecorder(session_id="s1", user_id="alice")
    with recorder.span("op", kind="tool"):
        pass
    trace = recorder.finish()

    otel_spans = to_otel_spans(trace)

    # Nanosecond timestamps should be much larger than the raw monotonic
    # seconds value used internally.
    assert otel_spans[0].start_time_unix_nano > 1_000_000_000


def test_to_otel_spans_maps_error_status():
    recorder = TraceRecorder(session_id="s1", user_id="alice")
    try:
        with recorder.span("failing_op", kind="tool"):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    trace = recorder.finish(status="error")

    otel_spans = to_otel_spans(trace)

    assert otel_spans[0].status_code == "ERROR"


def test_in_memory_exporter_accumulates_spans():
    recorder = TraceRecorder(session_id="s1", user_id="alice")
    with recorder.span("op", kind="tool"):
        pass
    trace = recorder.finish()
    exporter = InMemoryOtelExporter()

    exporter.export(to_otel_spans(trace))

    assert len(exporter.exported) == 1
