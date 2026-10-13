from app.agents.base import AgentResponse
from app.evaluation.golden import GoldenCaseResult
from app.evaluation.llm_judge import JudgeScore
from app.evaluation.outcome_trajectory_quality import (
    TrajectoryExpectation,
    build_evaluation_result,
    score_outcome,
    score_trajectory,
)


def _response(agent: str = "research_agent", tool_calls: list[str] = None, stop_reason: str = "task_completed") -> AgentResponse:
    return AgentResponse(
        input="test", output="answer", model="test-model", agent=agent,
        tool_calls=tool_calls or [], stop_reason=stop_reason,
    )


def test_score_outcome_wraps_golden_result_passed_as_is():
    golden_result = GoldenCaseResult(case_id="c1", passed=True, reason="All expectations met.")

    outcome = score_outcome(golden_result)

    assert outcome.passed is True
    assert outcome.reason == "All expectations met."


def test_score_trajectory_passes_when_agent_and_tools_match():
    response = _response(agent="research_agent", tool_calls=["retrieve"])
    expectation = TrajectoryExpectation(expected_agent="research_agent", expected_tools=["retrieve"])

    trajectory = score_trajectory(response, expectation)

    assert trajectory.passed is True


def test_score_trajectory_fails_on_wrong_agent_even_if_tools_match():
    response = _response(agent="planner_agent", tool_calls=["retrieve"])
    expectation = TrajectoryExpectation(expected_agent="research_agent", expected_tools=["retrieve"])

    trajectory = score_trajectory(response, expectation)

    assert trajectory.passed is False
    assert "research_agent" in trajectory.reason


def test_score_trajectory_fails_on_missing_tool():
    response = _response(agent="research_agent", tool_calls=[])
    expectation = TrajectoryExpectation(expected_agent="research_agent", expected_tools=["retrieve"])

    trajectory = score_trajectory(response, expectation)

    assert trajectory.passed is False
    assert "retrieve" in trajectory.reason


def test_score_trajectory_enforces_tool_order_when_requested():
    response = _response(agent="research_agent", tool_calls=["calculator", "retrieve"])
    expectation = TrajectoryExpectation(
        expected_agent="research_agent", expected_tools=["retrieve", "calculator"], expected_tool_order=True,
    )

    trajectory = score_trajectory(response, expectation)

    assert trajectory.passed is False
    assert "order" in trajectory.reason.lower()


def test_score_trajectory_fails_on_unhealthy_stop_reason():
    """A response that stopped because it ran out of budget took a real,
    broken path -- trajectory must fail regardless of what the final
    text looks like."""
    response = _response(agent="research_agent", tool_calls=["retrieve"], stop_reason="budget_exhausted")
    expectation = TrajectoryExpectation(expected_agent="research_agent", expected_tools=["retrieve"])

    trajectory = score_trajectory(response, expectation)

    assert trajectory.passed is False
    assert "budget_exhausted" in trajectory.reason


def test_outcome_pass_trajectory_fail_is_the_real_previously_hidden_case():
    """The whole point of separating these two: a case can get the right
    FINAL answer via the WRONG agent -- outcome=pass, trajectory=fail.
    A single blended boolean (this project's old run_golden_case() check)
    could never distinguish this from a genuinely clean pass."""
    golden_result = GoldenCaseResult(case_id="c1", passed=True, reason="Final answer matched.")
    response = _response(agent="planner_agent")  # wrong agent, but the golden check only looks at the final answer
    expectation = TrajectoryExpectation(expected_agent="research_agent")

    result = build_evaluation_result("c1", golden_result, response, expectation)

    assert result.outcome.passed is True
    assert result.trajectory.passed is False
    assert result.outcome_trajectory_agree is False


def test_outcome_and_trajectory_agreeing_is_the_normal_clean_case():
    golden_result = GoldenCaseResult(case_id="c1", passed=True, reason="Final answer matched.")
    response = _response(agent="research_agent", tool_calls=["retrieve"])
    expectation = TrajectoryExpectation(expected_agent="research_agent", expected_tools=["retrieve"])

    result = build_evaluation_result("c1", golden_result, response, expectation)

    assert result.outcome_trajectory_agree is True


def test_build_evaluation_result_carries_quality_when_given():
    golden_result = GoldenCaseResult(case_id="c1", passed=True, reason="ok")
    response = _response()
    expectation = TrajectoryExpectation()
    quality = JudgeScore(correctness=0.9, completeness=0.8, groundedness=0.95, citation_quality=0.7, instruction_following=0.85, overall=0.85)

    result = build_evaluation_result("c1", golden_result, response, expectation, quality=quality)

    assert result.quality.overall == 0.85


def test_build_evaluation_result_quality_defaults_to_none():
    golden_result = GoldenCaseResult(case_id="c1", passed=True, reason="ok")
    response = _response()
    expectation = TrajectoryExpectation()

    result = build_evaluation_result("c1", golden_result, response, expectation)

    assert result.quality is None


def test_outcome_trajectory_agree_is_not_a_dumped_field():
    """Real, found bug while building scripts/generate_outcome_trajectory_
    quality_demo.py: outcome_trajectory_agree is a @property, not a
    pydantic field, so model_dump() silently omits it -- a caller that
    serializes an EvaluationResult and later reads this key back must
    compute it explicitly first, as the generator script now does."""
    golden_result = GoldenCaseResult(case_id="c1", passed=True, reason="ok")
    response = _response()
    expectation = TrajectoryExpectation()

    result = build_evaluation_result("c1", golden_result, response, expectation)
    dumped = result.model_dump()

    assert "outcome_trajectory_agree" not in dumped
