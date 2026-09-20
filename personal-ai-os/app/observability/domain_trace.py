from app.observability.traces import Trace, TraceRecorder


def new_domain_journey(session_id: str, user_id: str) -> TraceRecorder:
    """Section 41: 'Every request should have a Journey ID.' Phase 1's
    Trace.execution_id (Milestone 12) already IS a journey id — this helper
    exists only to document the intended span shape for a domain request
    (Section 41's example: User -> Domain Router -> Career Agent -> Resume
    Retrieval -> RAG -> LLM -> Evaluator), so callers building a domain
    workflow's tracing know which span kinds/names to use, e.g.:

        recorder = new_domain_journey(session_id, user_id)
        with recorder.span("domain_router", kind="classification"):
            ...
        with recorder.span("career_agent", kind="agent"):
            with recorder.span("resume_retrieval", kind="retrieval"):
                ...
            with recorder.span("llm_call", kind="llm"):
                ...
        with recorder.span("evaluator", kind="evaluation"):
            ...
        trace = recorder.finish()

    No new Trace/Span schema is introduced — this is Phase 1's TraceRecorder,
    used as-is."""
    return TraceRecorder(session_id=session_id, user_id=user_id)


def journey_id(trace: Trace) -> str:
    """Section 41's 'journey_123' example, made explicit: the journey id IS
    the trace's execution_id — this accessor exists so calling code can refer
    to 'the journey id' by name without needing to know it's the same field."""
    return trace.execution_id
