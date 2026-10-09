"""Real, live grading harness for evals/career/*.json, found missing
while investigating "AI Evaluation" (disclosed gap: "the domain-specific
synthetic sets (career/pm/finance/learning/cross_domain) still have no
live grading harness (a different input shape per domain)"). Career is
built first as the representative close -- each case's `category`
(jd_analysis/interview_prep/resume_optimization) dispatches to the real
domain workflow function it names, reusing this project's own real
career_eval.py checks plus the real grounding checks already built for
each workflow (Section 10 rule 6: never invent an achievement).
"""

from pydantic import BaseModel

from app.domains.career.interview_prep import NoRelevantExperienceError, build_interview_story
from app.domains.career.jd_analysis import analyze_jd
from app.domains.career.resume_optimization import check_outcome_grounded, optimize_resume
from app.evaluation.career_eval import check_jd_analysis_scores_in_range, check_star_completeness
from app.evaluation.domain_golden import DomainGoldenCase
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.base import LLMProvider


class CareerGoldenCaseResult(BaseModel):
    case_id: str
    category: str
    passed: bool
    reason: str


def run_career_golden_case(
    llm: LLMProvider, secure_retriever: SecureRetriever, requester_id: str, requester_tenant_id: str,
    case: DomainGoldenCase,
) -> CareerGoldenCaseResult:
    if case.category == "jd_analysis":
        result = analyze_jd(llm, case.input, secure_retriever, requester_id, requester_tenant_id)
        check = check_jd_analysis_scores_in_range(result)
        return CareerGoldenCaseResult(case_id=case.id, category=case.category, passed=check.passed, reason=check.reason)

    if case.category == "interview_prep":
        try:
            story = build_interview_story(llm, case.input, secure_retriever, requester_id, requester_tenant_id)
        except NoRelevantExperienceError as exc:
            return CareerGoldenCaseResult(
                case_id=case.id, category=case.category, passed=False,
                reason=f"No relevant experience found (real, honest outcome, not a crash): {exc}",
            )
        check = check_star_completeness(story)
        return CareerGoldenCaseResult(case_id=case.id, category=case.category, passed=check.passed, reason=check.reason)

    if case.category == "resume_optimization":
        outcome = optimize_resume(llm, case.input, secure_retriever, requester_id, requester_tenant_id)
        grounded = check_outcome_grounded(outcome)
        reason = "All suggestions grounded in real retrieved excerpts." if grounded else "A suggestion cited an excerpt id that was never retrieved -- likely fabricated."
        return CareerGoldenCaseResult(case_id=case.id, category=case.category, passed=grounded, reason=reason)

    return CareerGoldenCaseResult(
        case_id=case.id, category=case.category, passed=False,
        reason=f"Unknown category '{case.category}' -- no real workflow dispatch exists for it.",
    )


def run_career_golden_suite(
    llm: LLMProvider, secure_retriever: SecureRetriever, requester_id: str, requester_tenant_id: str,
    cases: list[DomainGoldenCase],
) -> list[CareerGoldenCaseResult]:
    return [run_career_golden_case(llm, secure_retriever, requester_id, requester_tenant_id, case) for case in cases]
