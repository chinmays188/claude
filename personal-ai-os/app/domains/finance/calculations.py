"""Deterministic financial arithmetic. Section 24: 'Do not use an LLM for
arithmetic that can be performed deterministically.' Every function here is
pure Python math — no LLM call anywhere in this module. This is the load-
bearing safety property of Finance OS: a portfolio value or a scenario loss
must be exactly reproducible and auditable, not a plausible-sounding LLM guess."""

from app.domains.finance.models import Goal, Holding, Loan, Portfolio


def portfolio_total_value(portfolio: Portfolio) -> float:
    return sum(h.current_value for h in portfolio.holdings)


def portfolio_total_cost_basis(portfolio: Portfolio) -> float:
    return sum(h.cost_basis for h in portfolio.holdings)


def portfolio_unrealized_gain(portfolio: Portfolio) -> float:
    return portfolio_total_value(portfolio) - portfolio_total_cost_basis(portfolio)


def asset_class_allocation(portfolio: Portfolio) -> dict[str, float]:
    """Fraction of total portfolio value per asset class. Empty portfolio
    returns an empty dict rather than raising or dividing by zero."""
    total = portfolio_total_value(portfolio)
    if total == 0:
        return {}

    totals: dict[str, float] = {}
    for holding in portfolio.holdings:
        totals[holding.asset_class.value] = totals.get(holding.asset_class.value, 0.0) + holding.current_value

    return {asset_class: value / total for asset_class, value in totals.items()}


def concentration_ratio(portfolio: Portfolio) -> float:
    """Section 23: 'Concentration.' Fraction of total value held in the single
    largest holding — a simple, well-defined concentration-risk proxy."""
    total = portfolio_total_value(portfolio)
    if total == 0 or not portfolio.holdings:
        return 0.0
    largest = max(h.current_value for h in portfolio.holdings)
    return largest / total


class ScenarioResult:
    def __init__(self, current_value: float, shock_pct: float, new_value: float, loss: float):
        self.current_value = current_value
        self.shock_pct = shock_pct
        self.new_value = new_value
        self.loss = loss


def apply_scenario_shock(portfolio: Portfolio, shock_pct: float) -> ScenarioResult:
    """Section 24: 'What happens if my portfolio falls 20%?' shock_pct is
    negative for a decline (e.g. -0.20 for a 20% fall). Pure arithmetic, no LLM."""
    current_value = portfolio_total_value(portfolio)
    new_value = current_value * (1 + shock_pct)
    loss = current_value - new_value
    return ScenarioResult(current_value=current_value, shock_pct=shock_pct, new_value=new_value, loss=loss)


def recovery_return_required(new_value: float, target_value: float) -> float:
    """After a loss, what % return is needed to get back to target_value?
    Note the asymmetry: a 20% loss requires a 25% gain to recover, not 20%."""
    if new_value <= 0:
        raise ValueError("new_value must be positive to compute a recovery return.")
    return (target_value - new_value) / new_value


def goal_projection(goal: Goal, monthly_contribution: float, annual_return_rate: float) -> float:
    """Projects the goal's future value after monthly contributions compounded
    at annual_return_rate until target_date. annual_return_rate is an
    ASSUMPTION the caller must supply and tag as such (Section 23) — this
    function does not fabricate a return rate."""
    from datetime import date

    months_remaining = _months_between(date.today(), goal.target_date)
    if months_remaining <= 0:
        return goal.current_amount

    monthly_rate = annual_return_rate / 12
    value = goal.current_amount
    for _ in range(months_remaining):
        value = value * (1 + monthly_rate) + monthly_contribution
    return value


def sip_projection(monthly_contribution: float, annual_return_rate: float, months: int) -> float:
    """Standard SIP (systematic investment plan) future-value calculation,
    starting from zero."""
    if months <= 0:
        return 0.0
    monthly_rate = annual_return_rate / 12
    value = 0.0
    for _ in range(months):
        value = value * (1 + monthly_rate) + monthly_contribution
    return value


def loan_payoff_months(loan: Loan) -> int:
    """Given the loan's principal, rate, and fixed monthly payment, how many
    months until it's paid off? Standard amortization loop, deterministic."""
    if loan.monthly_payment <= 0:
        raise ValueError("monthly_payment must be positive.")

    balance = loan.principal
    monthly_rate = loan.annual_rate / 12
    months = 0
    max_months = 100 * 12  # guardrail against an infinite loop on a payment too small to ever amortize

    while balance > 0 and months < max_months:
        interest = balance * monthly_rate
        principal_payment = loan.monthly_payment - interest
        if principal_payment <= 0:
            raise ValueError(
                "monthly_payment does not cover interest — loan would never amortize at this payment."
            )
        balance -= principal_payment
        months += 1

    return months


def _months_between(start: "date", end: "date") -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)
