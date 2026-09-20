from app.observability.domain_trace import journey_id, new_domain_journey


def test_new_domain_journey_returns_working_recorder():
    recorder = new_domain_journey(session_id="s1", user_id="alice")

    with recorder.span("domain_router", kind="classification"):
        pass
    with recorder.span("career_agent", kind="agent"):
        with recorder.span("resume_retrieval", kind="retrieval"):
            pass

    trace = recorder.finish()

    assert trace.retrieval_calls == 1
    assert len(trace.spans) == 2


def test_journey_id_is_the_execution_id():
    recorder = new_domain_journey(session_id="s1", user_id="alice")
    trace = recorder.finish()

    assert journey_id(trace) == trace.execution_id
