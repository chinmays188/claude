"""Splits agent evaluation into 3 explicit, independently-scored parts,
per the user's ask: "we should divide our entire evals into outcome,
trajectory and quality for each evaluation."

Checked first, honestly: this project's evals blurred two of the three
together. `run_golden_case()` (app/evaluation/golden.py) checks the
final agent/tools in ONE boolean -- a case that reaches the right final
answer via the WRONG path (e.g. the planner agent instead of the
research agent, or calling an unexpected tool first) currently shows as
a clean pass, with no visibility into HOW it got there. `judge_response()`
(app/evaluation/llm_judge.py)'s 6 dimensions were real but flat, never
grouped under a "quality" umbrella or explicitly separated from
correctness.

This module is pure composition, not a replacement: it WRAPS the
existing, unchanged GoldenCaseResult + JudgeScore rather than
reimplementing either.

- OUTCOME: did the final result match what was expected? (reuses
  GoldenCaseResult.passed as-is -- this project's existing notion of
  "did it get the right answer" already IS the outcome check, it was
  just never named that way or separated from trajectory.)
- TRAJECTORY: did the agent take the right PATH to get there -- right
  agent dispatched, right tools called (and in the expected order, when
  an order is specified), stopped for a real, healthy reason (not
  budget-exhausted or an error)? Scored independently of whether the
  final answer happened to be right.
- QUALITY: how GOOD was the output, independent of raw correctness --
  groundedness, citation quality, instruction-following (JudgeScore's
  existing 6 dimensions, now explicitly grouped under this umbrella).
"""

from pydantic import BaseModel

from app.agents.base import AgentResponse
from app.evaluation.golden import GoldenCase, GoldenCaseResult
from app.evaluation.llm_judge import JudgeScore

# Stop reasons considered "healthy" for trajectory purposes -- a request
# that stopped because it ran out of budget or hit an unrecovered error
# took a real, broken path regardless of what the final text says.
_HEALTHY_STOP_REASONS = {"task_completed", "approval_pending"}


class TrajectoryExpectation(BaseModel):
    """What a real, correct PATH looks like for one case -- separate from
    GoldenCase's existing expected_agent/expected_tools so this module
    doesn't need to change that class's contract; a caller builds this
    from the same GoldenCase fields it already has."""

    expected_agent: str | None = None
    expected_tools: list[str] = []
    expected_tool_order: bool = False  # if True, tools must appear in this exact order, not just be present


class TrajectoryScore(BaseModel):
    passed: bool
    reason: str
    actual_agent: str | None = None
    actual_tools: list[str] = []
    actual_stop_reason: str | None = None


class OutcomeScore(BaseModel):
    passed: bool
    reason: str


class EvaluationResult(BaseModel):
    """Real, inspectable result carrying all 3 scores for ONE case --
    the whole point is that a caller (or the dashboard) can see all 3
    independently, including the real, previously-invisible case of
    outcome=pass but trajectory=fail."""

    case_id: str
    outcome: OutcomeScore
    trajectory: TrajectoryScore
    quality: JudgeScore | None = None  # None when no LLM-judge call was made for this case

    @property
    def outcome_trajectory_agree(self) -> bool:
        """False is the real, previously-hidden signal this module exists
        to surface: the final answer was right, but for the wrong reason
        (or vice versa) -- a genuine red flag an outcome-only pass/fail
        can never show."""
        return self.outcome.passed == self.trajectory.passed


def score_outcome(golden_result: GoldenCaseResult) -> OutcomeScore:
    """Thin wrapper -- GoldenCaseResult.passed already IS this project's
    real outcome check (did the final agent/answer match what was
    expected); this just names it explicitly rather than leaving it
    nameless inside a general-purpose result object."""
    return OutcomeScore(passed=golden_result.passed, reason=golden_result.reason)


def score_trajectory(response: AgentResponse, expectation: TrajectoryExpectation) -> TrajectoryScore:
    """Scores the PATH independently of the final answer. A response can
    score outcome=pass and trajectory=fail (right answer, wrong path --
    e.g. got lucky, or a tool call that happened to not matter for this
    particular input) or outcome=fail and trajectory=pass (right path,
    but the agent's own reasoning on top of correct retrieval/tool-calls
    was wrong) -- both are real, distinct, actionable failure modes a
    single blended check can't tell apart."""
    if response.stop_reason not in _HEALTHY_STOP_REASONS:
        return TrajectoryScore(
            passed=False, reason=f"Stopped for an unhealthy reason: '{response.stop_reason}'.",
            actual_agent=response.agent, actual_tools=response.tool_calls, actual_stop_reason=response.stop_reason,
        )

    if expectation.expected_agent is not None and response.agent != expectation.expected_agent:
        return TrajectoryScore(
            passed=False,
            reason=f"Expected agent '{expectation.expected_agent}', got '{response.agent}'.",
            actual_agent=response.agent, actual_tools=response.tool_calls, actual_stop_reason=response.stop_reason,
        )

    if expectation.expected_tool_order:
        if response.tool_calls[: len(expectation.expected_tools)] != expectation.expected_tools:
            return TrajectoryScore(
                passed=False,
                reason=f"Expected tool order {expectation.expected_tools}, got {response.tool_calls}.",
                actual_agent=response.agent, actual_tools=response.tool_calls, actual_stop_reason=response.stop_reason,
            )
    else:
        missing_tools = set(expectation.expected_tools) - set(response.tool_calls)
        if missing_tools:
            return TrajectoryScore(
                passed=False,
                reason=f"Expected tool(s) {sorted(missing_tools)} were not called.",
                actual_agent=response.agent, actual_tools=response.tool_calls, actual_stop_reason=response.stop_reason,
            )

    return TrajectoryScore(
        passed=True, reason="Agent and tool path matched expectations.",
        actual_agent=response.agent, actual_tools=response.tool_calls, actual_stop_reason=response.stop_reason,
    )


def build_evaluation_result(
    case_id: str, golden_result: GoldenCaseResult, response: AgentResponse,
    expectation: TrajectoryExpectation, quality: JudgeScore | None = None,
) -> EvaluationResult:
    """Composes all 3 real scores for one case into a single, inspectable
    result -- the caller already has golden_result (from run_golden_case())
    and response (Orchestrator.handle()'s own return value for that case),
    so this is pure composition over values the caller already computed,
    not a second real execution."""
    return EvaluationResult(
        case_id=case_id,
        outcome=score_outcome(golden_result),
        trajectory=score_trajectory(response, expectation),
        quality=quality,
    )
