"""Real grading harness for evals/finance/*.json, found missing while
investigating "AI Evaluation" (disclosed gap: domain-specific golden
sets have no live grading harness). A real, honest finding specific to
this domain: scenario_analysis's analyze_scenario() takes no LLM
parameter at all (Section 24: "an LLM should never compute or restate a
scenario shock's numbers itself") -- so finance_002's "live" grading is
genuinely just confirming the deterministic calculation is correct, no
Gemini call involved for that case. portfolio_analysis's
analyze_portfolio() DOES make a real LLM call (for ASSUMPTION/OPINION
commentary only, never arithmetic), so finance_001 is graded live.
"""

from datetime import date

from pydantic import BaseModel

from app.domains.finance.models import Holding, Portfolio
from app.domains.finance.portfolio_analysis import analyze_portfolio
from app.domains.finance.scenario_analysis import analyze_scenario
from app.evaluation.domain_golden import DomainGoldenCase
from app.evaluation.finance_eval import check_all_claims_tagged, check_calculations_match_deterministic_values
from app.providers.base import LLMProvider


class FinanceGoldenCaseResult(BaseModel):
    case_id: str
    category: str
    passed: bool
    reason: str


def _portfolio_from_input(input_dict: dict) -> Portfolio:
    holdings = [Holding(**h) for h in input_dict["holdings"]]
    return Portfolio(owner_id="demo_user", as_of=date.today(), holdings=holdings)


def run_finance_golden_case(llm: LLMProvider, case: DomainGoldenCase, fixture_portfolio: Portfolio) -> FinanceGoldenCaseResult:
    if case.category == "portfolio_analysis":
        portfolio = _portfolio_from_input(case.input)
        result = analyze_portfolio(llm, portfolio)
        check = check_all_claims_tagged(result.claims)
        return FinanceGoldenCaseResult(case_id=case.id, category=case.category, passed=check.passed, reason=check.reason)

    if case.category == "scenario_analysis":
        # Real, honest finding: no LLM call happens for this category at
        # all (Section 24's absolute rule) -- "live grading" here means
        # confirming the deterministic calculation itself is correct.
        shock_pct = case.input["shock_pct"]
        result = analyze_scenario(fixture_portfolio, shock_pct)
        from app.domains.finance.calculations import apply_scenario_shock

        expected = apply_scenario_shock(fixture_portfolio, shock_pct)
        check = check_calculations_match_deterministic_values(
            result.claims,
            {"Projected value after shock": expected.new_value, "Projected loss": expected.loss},
        )
        return FinanceGoldenCaseResult(case_id=case.id, category=case.category, passed=check.passed, reason=check.reason)

    return FinanceGoldenCaseResult(
        case_id=case.id, category=case.category, passed=False,
        reason=f"Unknown category '{case.category}' -- no real workflow dispatch exists for it.",
    )


def run_finance_golden_suite(llm: LLMProvider, cases: list[DomainGoldenCase], fixture_portfolio: Portfolio) -> list[FinanceGoldenCaseResult]:
    return [run_finance_golden_case(llm, case, fixture_portfolio) for case in cases]
