"""Real, live grading harness for evals/pm/*.json, found missing while
investigating "AI Evaluation" (disclosed gap: "the domain-specific
synthetic sets ... still have no live grading harness"). Same pattern
as career_golden_runner.py: each case's `category`
(feedback_intelligence/stakeholder_request/prd_generation) dispatches
to the real domain workflow function it names, reusing this project's
own real pm_eval.py checks.
"""

from pydantic import BaseModel

from app.domains.pm.feedback_intelligence import analyze_feedback
from app.domains.pm.prd import draft_and_critique_prd
from app.domains.pm.stakeholder_request import analyze_stakeholder_request
from app.evaluation.domain_golden import DomainGoldenCase
from app.evaluation.pm_eval import (
    check_critic_challenged_the_prd,
    check_feedback_themes_grounded,
    check_stakeholder_recommendation_reasoned,
)
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.base import LLMProvider


class PmGoldenCaseResult(BaseModel):
    case_id: str
    category: str
    passed: bool
    reason: str


def run_pm_golden_case(
    llm: LLMProvider, secure_retriever: SecureRetriever, requester_id: str, requester_tenant_id: str,
    case: DomainGoldenCase,
) -> PmGoldenCaseResult:
    if case.category == "feedback_intelligence":
        feedback_items = case.input if isinstance(case.input, list) else [case.input]
        result = analyze_feedback(llm, feedback_items)
        check = check_feedback_themes_grounded(result, feedback_items)
        return PmGoldenCaseResult(case_id=case.id, category=case.category, passed=check.passed, reason=check.reason)

    if case.category == "stakeholder_request":
        result = analyze_stakeholder_request(llm, case.input, secure_retriever, requester_id, requester_tenant_id)
        check = check_stakeholder_recommendation_reasoned(result)
        return PmGoldenCaseResult(case_id=case.id, category=case.category, passed=check.passed, reason=check.reason)

    if case.category == "prd_generation":
        critiqued = draft_and_critique_prd(llm, case.input, secure_retriever, requester_id, requester_tenant_id)
        check = check_critic_challenged_the_prd(critiqued.critique)
        return PmGoldenCaseResult(case_id=case.id, category=case.category, passed=check.passed, reason=check.reason)

    return PmGoldenCaseResult(
        case_id=case.id, category=case.category, passed=False,
        reason=f"Unknown category '{case.category}' -- no real workflow dispatch exists for it.",
    )


def run_pm_golden_suite(
    llm: LLMProvider, secure_retriever: SecureRetriever, requester_id: str, requester_tenant_id: str,
    cases: list[DomainGoldenCase],
) -> list[PmGoldenCaseResult]:
    return [run_pm_golden_case(llm, secure_retriever, requester_id, requester_tenant_id, case) for case in cases]
