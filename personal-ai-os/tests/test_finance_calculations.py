from datetime import date

import pytest

from app.domains.finance.calculations import (
    asset_class_allocation,
    apply_scenario_shock,
    concentration_ratio,
    goal_projection,
    loan_payoff_months,
    portfolio_total_cost_basis,
    portfolio_total_value,
    portfolio_unrealized_gain,
    recovery_return_required,
    sip_projection,
)
from app.domains.finance.models import AssetClass, Goal, Holding, Loan, Portfolio


def _holding(asset="Example Stock", asset_class=AssetClass.EQUITY, quantity=10, cost_basis=1000, current_value=1200) -> Holding:
    return Holding(asset=asset, asset_class=asset_class, quantity=quantity, cost_basis=cost_basis, current_value=current_value)


def _portfolio(holdings) -> Portfolio:
    return Portfolio(owner_id="alice", as_of=date(2026, 1, 1), holdings=holdings)


def test_portfolio_total_value():
    portfolio = _portfolio([_holding(current_value=1000), _holding(current_value=500)])

    assert portfolio_total_value(portfolio) == 1500


def test_portfolio_unrealized_gain():
    portfolio = _portfolio([_holding(cost_basis=1000, current_value=1200)])

    assert portfolio_unrealized_gain(portfolio) == 200


def test_asset_class_allocation_sums_to_one():
    portfolio = _portfolio(
        [_holding(asset_class=AssetClass.EQUITY, current_value=800), _holding(asset_class=AssetClass.DEBT, current_value=200)]
    )

    allocation = asset_class_allocation(portfolio)

    assert allocation["equity"] == pytest.approx(0.8)
    assert allocation["debt"] == pytest.approx(0.2)
    assert sum(allocation.values()) == pytest.approx(1.0)


def test_asset_class_allocation_empty_portfolio():
    assert asset_class_allocation(_portfolio([])) == {}


def test_concentration_ratio():
    portfolio = _portfolio([_holding(current_value=900), _holding(current_value=100)])

    assert concentration_ratio(portfolio) == pytest.approx(0.9)


def test_concentration_ratio_empty_portfolio():
    assert concentration_ratio(_portfolio([])) == 0.0


def test_apply_scenario_shock_negative():
    portfolio = _portfolio([_holding(current_value=1000)])

    result = apply_scenario_shock(portfolio, -0.20)

    assert result.new_value == pytest.approx(800)
    assert result.loss == pytest.approx(200)


def test_recovery_return_required_asymmetry():
    # A 20% loss (1000 -> 800) requires a 25% gain to recover, not 20%.
    recovery = recovery_return_required(new_value=800, target_value=1000)

    assert recovery == pytest.approx(0.25)


def test_recovery_return_required_rejects_zero_or_negative_new_value():
    with pytest.raises(ValueError):
        recovery_return_required(new_value=0, target_value=1000)


def test_goal_projection_grows_with_contributions():
    goal = Goal(goal_id="g1", title="Emergency fund", target_amount=10000, target_date=date.today().replace(year=date.today().year + 1), current_amount=0)

    projected = goal_projection(goal, monthly_contribution=500, annual_return_rate=0.06)

    assert projected > 500 * 12  # compounding should exceed pure contributions


def test_goal_projection_past_target_date_returns_current_amount():
    goal = Goal(goal_id="g1", title="Past goal", target_amount=10000, target_date=date(2020, 1, 1), current_amount=5000)

    projected = goal_projection(goal, monthly_contribution=500, annual_return_rate=0.06)

    assert projected == 5000


def test_sip_projection_zero_months():
    assert sip_projection(500, 0.06, months=0) == 0.0


def test_sip_projection_positive():
    result = sip_projection(1000, 0.08, months=12)

    assert result > 1000 * 12  # compounding effect


def test_loan_payoff_months_reasonable():
    loan = Loan(loan_id="l1", principal=10000, annual_rate=0.10, remaining_term_months=24, monthly_payment=500)

    months = loan_payoff_months(loan)

    assert 20 <= months <= 24


def test_loan_payoff_months_rejects_non_positive_payment():
    loan = Loan(loan_id="l1", principal=10000, annual_rate=0.10, remaining_term_months=24, monthly_payment=0)

    with pytest.raises(ValueError):
        loan_payoff_months(loan)


def test_loan_payoff_months_rejects_payment_below_interest():
    loan = Loan(loan_id="l1", principal=10000, annual_rate=0.24, remaining_term_months=24, monthly_payment=100)

    with pytest.raises(ValueError):
        loan_payoff_months(loan)
