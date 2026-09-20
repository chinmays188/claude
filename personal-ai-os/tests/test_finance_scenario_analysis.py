from datetime import date

import pytest

from app.domains.finance.models import AssetClass, ClaimKind, Holding, Portfolio
from app.domains.finance.scenario_analysis import analyze_scenario


def _portfolio() -> Portfolio:
    return Portfolio(
        owner_id="alice", as_of=date(2026, 1, 1),
        holdings=[Holding(asset="Stock A", asset_class=AssetClass.EQUITY, quantity=10, cost_basis=1000, current_value=1000)],
    )


def test_scenario_analysis_has_no_llm_dependency():
    # No LLMProvider argument at all -- this function cannot call an LLM,
    # by construction (Section 24's rule made structural, not just documented).
    import inspect

    from app.domains.finance import scenario_analysis

    sig = inspect.signature(scenario_analysis.analyze_scenario)
    assert "llm" not in sig.parameters


def test_scenario_analysis_computes_correct_loss():
    result = analyze_scenario(_portfolio(), shock_pct=-0.20)

    loss_claims = [c for c in result.claims if "loss" in c.text.lower()]
    assert any(c.value == 200 for c in loss_claims)


def test_scenario_analysis_tags_shock_as_assumption():
    result = analyze_scenario(_portfolio(), shock_pct=-0.20)

    shock_claims = [c for c in result.claims if "shock applied" in c.text.lower()]
    assert len(shock_claims) == 1
    assert shock_claims[0].kind == ClaimKind.ASSUMPTION


def test_scenario_analysis_includes_recovery_when_target_given():
    result = analyze_scenario(_portfolio(), shock_pct=-0.20, target_value=1000)

    recovery_claims = [c for c in result.claims if "return required" in c.text.lower()]
    assert len(recovery_claims) == 1
    assert recovery_claims[0].value == pytest.approx(0.25)


def test_scenario_analysis_omits_recovery_when_no_target():
    result = analyze_scenario(_portfolio(), shock_pct=-0.20)

    recovery_claims = [c for c in result.claims if "return required" in c.text.lower()]
    assert recovery_claims == []
