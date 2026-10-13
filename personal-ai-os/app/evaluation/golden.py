from pydantic import BaseModel

from app.agents.base import AgentResponse
from app.agents.orchestrator import ClarificationNeeded, Orchestrator


class GoldenCase(BaseModel):
    id: str
    input: str
    expected_agent: str | None = None  # None means ClarificationNeeded is expected
    expected_capabilities: list[str] = []
    expected_tools: list[str] = []


class GoldenCaseResult(BaseModel):
    case_id: str
    passed: bool
    reason: str
    actual_agent: str | None = None
    actual_tools: list[str] = []


def run_golden_case(orchestrator: Orchestrator, case: GoldenCase) -> GoldenCaseResult:
    result = orchestrator.handle(case.input)

    if case.expected_agent is None:
        if isinstance(result, ClarificationNeeded):
            return GoldenCaseResult(case_id=case.id, passed=True, reason="Clarification requested as expected.")
        return GoldenCaseResult(
            case_id=case.id, passed=False,
            reason=f"Expected clarification, but got agent '{result.agent}'.",
            actual_agent=result.agent,
        )

    if isinstance(result, ClarificationNeeded):
        return GoldenCaseResult(
            case_id=case.id, passed=False,
            reason=f"Expected agent '{case.expected_agent}', but got a clarification request.",
        )

    if result.agent != case.expected_agent:
        return GoldenCaseResult(
            case_id=case.id, passed=False,
            reason=f"Expected agent '{case.expected_agent}', got '{result.agent}'.",
            actual_agent=result.agent,
        )

    missing_tools = set(case.expected_tools) - set(result.tool_calls)
    if missing_tools:
        return GoldenCaseResult(
            case_id=case.id, passed=False,
            reason=f"Expected tool(s) {sorted(missing_tools)} were not called.",
            actual_agent=result.agent, actual_tools=result.tool_calls,
        )

    return GoldenCaseResult(
        case_id=case.id, passed=True, reason="All expectations met.",
        actual_agent=result.agent, actual_tools=result.tool_calls,
    )


def run_golden_set(orchestrator: Orchestrator, cases: list[GoldenCase]) -> list[GoldenCaseResult]:
    return [run_golden_case(orchestrator, case) for case in cases]


def pass_rate(results: list[GoldenCaseResult]) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r.passed) / len(results)


def run_golden_set_multi(orchestrator: Orchestrator, cases: list[GoldenCase], n_runs: int) -> tuple[int, int]:
    """Real multi-run execution, found missing per the user's shared
    eval-methodology excerpt: 'multiple eval runs are an operational
    necessity when measuring uncertainty.' Runs the FULL golden set
    n_runs times against the real, live orchestrator (each run is a
    genuinely separate real LLM call per case, not a cached replay --
    this project's own routing/classification calls are confirmed not
    perfectly deterministic even at temperature=0.0) and returns
    (total_successes, total_n) -- a (successes, trials) pair ready for
    app/evaluation/confidence.py's wilson_interval()/compare_pass_rates(),
    which need real counts, not just a single pre-computed rate."""
    total_successes = 0
    total_n = 0
    for _ in range(n_runs):
        results = run_golden_set(orchestrator, cases)
        total_successes += sum(1 for r in results if r.passed)
        total_n += len(results)
    return total_successes, total_n
