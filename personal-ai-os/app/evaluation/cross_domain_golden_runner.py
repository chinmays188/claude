"""Real grading harness for evals/cross_domain/*.json, found missing
while investigating "AI Evaluation" (disclosed gap: domain-specific
golden sets have no live grading harness). These cases test
DomainRouter's real multi-label classification directly -- no category
dispatch needed, unlike career/pm/finance/learning.
"""

from pydantic import BaseModel

from app.domains.router import Domain, DomainRouter
from app.evaluation.cross_domain_eval import check_correct_domain_selection
from app.evaluation.domain_golden import DomainGoldenCase
from app.providers.base import LLMProvider


class CrossDomainGoldenCaseResult(BaseModel):
    case_id: str
    passed: bool
    reason: str


def run_cross_domain_golden_case(llm: LLMProvider, case: DomainGoldenCase) -> CrossDomainGoldenCaseResult:
    router = DomainRouter(llm)
    classification = router.route(case.input)

    expected_domains = {Domain(d) for d in case.expected_domains}
    check = check_correct_domain_selection(classification.domains, expected_domains)
    return CrossDomainGoldenCaseResult(case_id=case.id, passed=check.passed, reason=check.reason)


def run_cross_domain_golden_suite(llm: LLMProvider, cases: list[DomainGoldenCase]) -> list[CrossDomainGoldenCaseResult]:
    return [run_cross_domain_golden_case(llm, case) for case in cases]
