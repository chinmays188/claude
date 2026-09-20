from datetime import date

from app.domains.finance.models import AssetClass, ClaimKind, Holding, Portfolio
from app.domains.finance.portfolio_analysis import analyze_portfolio
from app.evaluation.finance_eval import (
    check_all_claims_tagged,
    check_calculations_match_deterministic_values,
)
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _portfolio() -> Portfolio:
    return Portfolio(
        owner_id="alice", as_of=date(2026, 1, 1),
        holdings=[
            Holding(asset="Stock A", asset_class=AssetClass.EQUITY, quantity=10, cost_basis=1000, current_value=1200),
            Holding(asset="Bond A", asset_class=AssetClass.DEBT, quantity=1, cost_basis=500, current_value=500),
        ],
    )


def test_analyze_portfolio_includes_deterministic_fact_claims():
    llm = ScriptedProvider(['{"claims": [{"text": "Your portfolio is reasonably diversified.", "kind": "OPINION"}]}'])

    result = analyze_portfolio(llm, _portfolio())

    fact_claims = [c for c in result.claims if c.kind == ClaimKind.FACT]
    assert any("1700" in c.text or "1700.00" in c.text for c in fact_claims)  # total value = 1200 + 500


def test_analyze_portfolio_calculations_match_deterministic_math():
    llm = ScriptedProvider(['{"claims": []}'])

    result = analyze_portfolio(llm, _portfolio())

    check = check_calculations_match_deterministic_values(result.claims, expected_values={"unrealized gain": 200.0})
    assert check.passed


def test_analyze_portfolio_all_claims_tagged():
    llm = ScriptedProvider(['{"claims": [{"text": "Consider rebalancing.", "kind": "OPINION"}]}'])

    result = analyze_portfolio(llm, _portfolio())

    assert check_all_claims_tagged(result.claims).passed


def test_analyze_portfolio_appends_llm_observations_as_opinion_or_assumption():
    llm = ScriptedProvider(
        ['{"claims": [{"text": "Assuming continued market conditions, this allocation seems reasonable.", "kind": "ASSUMPTION"}, '
         '{"text": "You may want to diversify further.", "kind": "OPINION"}]}']
    )

    result = analyze_portfolio(llm, _portfolio())

    kinds = {c.kind for c in result.claims}
    assert ClaimKind.ASSUMPTION in kinds
    assert ClaimKind.OPINION in kinds
