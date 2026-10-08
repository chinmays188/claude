"""Real golden-set evaluation for PersonalContextEngine's scoring
weights, found missing while investigating "Context Engineering"
(disclosed gap: "PersonalContextEngine's scoring weights (relevance/
importance/freshness/confidence) are still fixed defaults, never tuned
or evaluated against a real golden set"). Same GoldenCase/
GoldenCaseResult pattern as app/evaluation/golden.py's real golden-case
runner, applied to context selection instead of routing.

Each case is a real, hand-crafted scenario with a human-judged correct
inclusion/exclusion outcome under a real token budget -- not invented
to flatter any particular weight configuration.
"""

from pydantic import BaseModel

from app.context.personal_context_engine import ContextItem, PersonalContextEngine


class ContextGoldenCase(BaseModel):
    id: str
    description: str
    items: list[dict]  # kwargs for ContextItem, minus the ones filled per-item below
    token_budget: int
    expected_included_contents: list[str]  # item.content values that MUST be selected


class ContextGoldenCaseResult(BaseModel):
    case_id: str
    passed: bool
    reason: str
    actual_included_contents: list[str]


def run_context_golden_case(
    engine: PersonalContextEngine, case: ContextGoldenCase, now=None
) -> ContextGoldenCaseResult:
    items = [ContextItem(**kwargs) for kwargs in case.items]
    selected = engine.select(items, token_budget=case.token_budget, now=now)
    actual_contents = [item.content for item in selected]

    missing = set(case.expected_included_contents) - set(actual_contents)
    if missing:
        return ContextGoldenCaseResult(
            case_id=case.id, passed=False,
            reason=f"Expected {sorted(case.expected_included_contents)} to be included, "
                   f"but {sorted(missing)} was excluded.",
            actual_included_contents=actual_contents,
        )
    return ContextGoldenCaseResult(
        case_id=case.id, passed=True, reason="All expected items selected.",
        actual_included_contents=actual_contents,
    )


def run_context_golden_suite(
    engine: PersonalContextEngine, cases: list[ContextGoldenCase], now=None
) -> list[ContextGoldenCaseResult]:
    return [run_context_golden_case(engine, case, now=now) for case in cases]


def accuracy(results: list[ContextGoldenCaseResult]) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r.passed) / len(results)
