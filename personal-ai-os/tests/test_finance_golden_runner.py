from datetime import date

from app.domains.finance.models import Holding, Portfolio
from app.evaluation.domain_golden import DomainGoldenCase
from app.evaluation.finance_golden_runner import run_finance_golden_case, run_finance_golden_suite
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _fixture_portfolio() -> Portfolio:
    return Portfolio(
        owner_id="demo_user", as_of=date.today(),
        holdings=[Holding(asset="Index Fund A", asset_class="equity", quantity=100, cost_basis=8000, current_value=9500)],
    )


def test_portfolio_analysis_case_passes_with_valid_claim_tags():
    llm = ScriptedProvider(['{"claims": [{"text": "Portfolio is well diversified for its size.", "kind": "OPINION"}]}'])
    case = DomainGoldenCase(id="finance_001", category="portfolio_analysis", input={"holdings": [{"asset": "Index Fund A", "asset_class": "equity", "quantity": 100, "cost_basis": 8000, "current_value": 9500}]})

    result = run_finance_golden_case(llm, case, _fixture_portfolio())

    assert result.passed is True
    assert result.category == "portfolio_analysis"


def test_scenario_analysis_case_needs_no_llm_call_at_all():
    """Real, honest finding: analyze_scenario() has no llm parameter --
    the ScriptedProvider here is given zero responses and must never be
    called, or the test itself would fail with an IndexError."""
    llm = ScriptedProvider([])  # if this is ever called, .generate() raises IndexError
    case = DomainGoldenCase(id="finance_002", category="scenario_analysis", input={"shock_pct": -0.2})

    result = run_finance_golden_case(llm, case, _fixture_portfolio())

    assert result.passed is True
    assert result.category == "scenario_analysis"


def test_unknown_category_fails_honestly():
    case = DomainGoldenCase(id="finance_999", category="not_real", input={})

    result = run_finance_golden_case(ScriptedProvider([]), case, _fixture_portfolio())

    assert result.passed is False
    assert "Unknown category" in result.reason


def test_run_finance_golden_suite_runs_every_case():
    llm = ScriptedProvider(['{"claims": [{"text": "Looks fine.", "kind": "OPINION"}]}'])
    cases = [DomainGoldenCase(id="finance_001", category="portfolio_analysis", input={"holdings": [{"asset": "A", "asset_class": "equity", "quantity": 1, "cost_basis": 100, "current_value": 110}]})]

    results = run_finance_golden_suite(llm, cases, _fixture_portfolio())

    assert len(results) == 1
