from enum import Enum

from pydantic import BaseModel

from app.observability.costs import JourneyCost


class BudgetAlertLevel(str, Enum):
    OK = "OK"
    WARNING = "WARNING"  # approaching the budget
    EXCEEDED = "EXCEEDED"  # over budget


class BudgetAlert(BaseModel):
    scope: str  # e.g. "journey:career_jd_analysis" or "domain:FINANCE"
    spent: float
    budget: float
    level: BudgetAlertLevel
    fraction_used: float


class CostBudget(BaseModel):
    scope: str
    limit: float
    warning_threshold: float = 0.8  # fraction of limit that triggers WARNING


class CostGovernor:
    """Milestone 55: 'AI Cost Governance.' Turns Phase 1's CostTracker
    (Milestone 13, after-the-fact reporting) into something that can actually
    alert BEFORE overspend — checked against a journey's running cost, not
    just reported once it's over. Does not itself block a request from
    running (that's a caller decision, e.g. refusing a new request when
    EXCEEDED); this only produces the signal to act on."""

    def __init__(self, budgets: dict[str, CostBudget]):
        self._budgets = budgets

    def check(self, scope: str, journey: JourneyCost) -> BudgetAlert:
        budget = self._budgets.get(scope)
        if budget is None:
            raise ValueError(f"No budget configured for scope '{scope}'.")

        spent = journey.total
        fraction = spent / budget.limit if budget.limit > 0 else float("inf")

        if spent > budget.limit:
            level = BudgetAlertLevel.EXCEEDED
        elif fraction >= budget.warning_threshold:
            level = BudgetAlertLevel.WARNING
        else:
            level = BudgetAlertLevel.OK

        return BudgetAlert(scope=scope, spent=spent, budget=budget.limit, level=level, fraction_used=fraction)

    def would_exceed(self, scope: str, journey: JourneyCost, additional_cost: float) -> bool:
        """Milestone 55's pre-flight check: would adding this much more cost
        push the journey over budget? Lets a caller refuse to start an
        expensive operation (e.g. a large LLM call) before it happens, not
        just report the overspend afterward."""
        budget = self._budgets.get(scope)
        if budget is None:
            raise ValueError(f"No budget configured for scope '{scope}'.")
        return (journey.total + additional_cost) > budget.limit
