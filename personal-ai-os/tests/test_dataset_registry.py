import time

from app.evaluation.dataset_registry import (
    DatasetType,
    classify_golden_cases,
    classify_synthetic_cases,
    production_dataset_non_goal_note,
    trace_to_golden_case,
)
from app.observability.traces import Span, Trace


def _span(name: str, agent: str | None, **extra_metadata) -> Span:
    now = time.monotonic()
    return Span(name=name, kind="agent", started_at=now, ended_at=now + 1, metadata={"agent": agent, **extra_metadata})


def _trace(agent_field: str, spans: list[Span]) -> Trace:
    return Trace(session_id="s1", user_id="u1", agent=agent_field, model="test-model", spans=spans)


def test_classify_golden_cases_tags_adversarial_ids_as_edge_case():
    entries = classify_golden_cases()

    edge_cases = [e for e in entries if e.dataset_type == DatasetType.EDGE_CASE]
    golden = [e for e in entries if e.dataset_type == DatasetType.GOLDEN]

    assert len(edge_cases) == 2
    assert all("_adversarial" in e.case_id for e in edge_cases)
    assert len(golden) >= 5
    assert all("_adversarial" not in e.case_id for e in golden)


def test_classify_synthetic_cases_covers_every_domain():
    entries = classify_synthetic_cases()

    assert all(e.dataset_type == DatasetType.SYNTHETIC for e in entries)
    assert len(entries) > 0


def test_production_dataset_non_goal_note_explains_the_absence():
    note = production_dataset_non_goal_note()

    assert "synthetic" in note.lower()
    assert "never" in note.lower() or "no " in note.lower()


def test_trace_to_golden_case_uses_real_agent_from_orchestrator_run_span():
    trace = _trace(agent_field="trace_request", spans=[_span("orchestrator_run", agent="research_agent")])

    case = trace_to_golden_case(trace, input_text="What is RAG?", case_id="c1")

    assert case.expected_agent == "research_agent"
    assert case.input == "What is RAG?"


def test_trace_to_golden_case_falls_back_to_none_for_the_known_placeholder_bug():
    """The real, found limitation: one of this project's own committed
    failure traces has metadata["agent"] == "agent" (a literal
    placeholder, a real bug in scripts/trace_request.py's own
    instrumentation) -- this must be treated as 'don't know', never
    silently promoted as if it were a real agent name."""
    trace = _trace(agent_field="trace_request", spans=[_span("orchestrator_run", agent="agent")])

    case = trace_to_golden_case(trace, input_text="Keep dividing by zero.", case_id="c2")

    assert case.expected_agent is None


def test_trace_to_golden_case_falls_back_to_none_when_no_orchestrator_run_span():
    trace = _trace(agent_field="trace_request", spans=[_span("retrieve_eval", agent=None)])

    case = trace_to_golden_case(trace, input_text="some query", case_id="c3")

    assert case.expected_agent is None


def test_trace_to_golden_case_never_trusts_the_top_level_agent_field():
    """The real, found limitation this function exists to work around:
    Trace.agent is set by whatever script generated the trace, not the
    real dispatched agent -- it must never be used directly."""
    trace = _trace(agent_field="trace_request", spans=[_span("orchestrator_run", agent="planner_agent")])

    case = trace_to_golden_case(trace, input_text="make a plan", case_id="c4")

    assert case.expected_agent == "planner_agent"  # from the span, not "trace_request"
