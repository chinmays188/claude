import sqlite3

from app.observability.traces import Span, Trace
from app.proactive.goal_run import GoalRun, GoalRunIteration, StopReason
from app.proactive.harness_feedback import (
    HarnessSuggestionStore,
    _build_evidence_block,
    generate_harness_suggestion,
)
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, response: str):
        self._response = response

    def generate(self, prompt: str) -> str:
        return self._response

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _failing_trace():
    span = Span(
        name="tool:calculator", kind="tool", started_at=0.0, ended_at=1.0,
        status="error", error="division by zero",
    )
    return Trace(session_id="s", user_id="demo_user", status="success", spans=[span])


def test_evidence_block_cites_real_failed_span_counts():
    traces = [_failing_trace(), Trace(session_id="s", user_id="demo_user", status="success")]

    block = _build_evidence_block(traces, [], [])

    assert "2 traces analyzed" in block
    assert "'tool': 1" in block  # real failed-span count by kind
    assert "division by zero" in block  # real example error text, not summarized away


def test_evidence_block_reports_real_error_rate_for_a_failed_trace():
    error_trace = Trace(session_id="s", user_id="demo_user", status="error")
    success_trace = Trace(session_id="s", user_id="demo_user", status="success")

    block = _build_evidence_block([error_trace, success_trace], [], [])

    assert "50.0%" in block


def test_evidence_block_reports_no_data_honestly():
    block = _build_evidence_block([], [], [])

    assert "0 traces analyzed" in block
    assert "none recorded yet" in block


def test_evidence_block_includes_goal_run_stats():
    run = GoalRun(
        goal_id="g1", owner_id="demo_user", input_text="x",
        iterations=[GoalRunIteration(iteration=1, output="o", achieved=True, reason="r")],
        stop_reason=StopReason.ACHIEVED.value, achieved=True,
    )

    block = _build_evidence_block([], [], [run])

    assert "1 runs" in block
    assert "achieved" in block


def test_evidence_block_includes_eval_harness_run_when_given():
    eval_run = {
        "golden_case_count": 5,
        "deterministic_pass_rate": 0.8,
        "average_judge_overall": 0.62,
        "results": [
            {
                "case_id": "research_002",
                "deterministic": {"passed": False, "reason": "Expected tool(s) ['calculator'] were not called."},
                "judge_score": {"overall": 0.5},
            },
        ],
    }

    block = _build_evidence_block([], [], [], eval_harness_run=eval_run)

    assert "5 cases" in block
    assert "80%" in block
    assert "research_002" in block
    assert "calculator" in block


def test_evidence_block_reports_no_eval_harness_run_honestly():
    block = _build_evidence_block([], [], [], eval_harness_run=None)

    assert "none recorded yet" in block


def test_generate_harness_suggestion_parses_real_llm_response():
    llm = ScriptedProvider(
        '{"has_suggestion": true, "suggestion": "Review calculator tool error handling.", '
        '"evidence_cited": "1 failed tool span", "reasoning": "A real tool failure was observed."}'
    )
    traces = [_failing_trace()]

    result = generate_harness_suggestion(llm, "demo_user", traces, [], [])

    assert result.has_suggestion is True
    assert "calculator" in result.suggestion
    assert result.evidence_cited


def test_generate_harness_suggestion_can_honestly_say_no_suggestion():
    llm = ScriptedProvider(
        '{"has_suggestion": false, "suggestion": "", "evidence_cited": "", '
        '"reasoning": "No failures or drift observed yet -- nothing to suggest."}'
    )

    result = generate_harness_suggestion(llm, "demo_user", [], [], [])

    assert result.has_suggestion is False
    assert result.suggestion == ""


def test_harness_suggestion_store_round_trips():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = HarnessSuggestionStore(conn)

    llm = ScriptedProvider('{"has_suggestion": false, "suggestion": "", "evidence_cited": "", "reasoning": "none"}')
    suggestion = generate_harness_suggestion(llm, "demo_user", [], [], [])
    store.save(suggestion)

    loaded = store.list_by_owner("demo_user")
    assert len(loaded) == 1
    assert loaded[0].suggestion_id == suggestion.suggestion_id


def test_harness_suggestion_store_is_idempotent_on_resave():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = HarnessSuggestionStore(conn)

    llm = ScriptedProvider('{"has_suggestion": false, "suggestion": "", "evidence_cited": "", "reasoning": "none"}')
    suggestion = generate_harness_suggestion(llm, "demo_user", [], [], [])
    store.save(suggestion)
    store.save(suggestion)

    assert len(store.list_by_owner("demo_user")) == 1
