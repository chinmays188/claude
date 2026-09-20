import pytest

from app.observability.costs import CostEntry, JourneyCost
from app.platform.cost_governance import BudgetAlertLevel, CostBudget, CostGovernor


def test_check_returns_ok_when_well_under_budget():
    governor = CostGovernor({"career": CostBudget(scope="career", limit=1.0, warning_threshold=0.8)})
    journey = JourneyCost(journey="j", entries=[CostEntry(component="c", cost=0.1)])

    alert = governor.check("career", journey)

    assert alert.level == BudgetAlertLevel.OK


def test_check_returns_warning_near_budget():
    governor = CostGovernor({"career": CostBudget(scope="career", limit=1.0, warning_threshold=0.8)})
    journey = JourneyCost(journey="j", entries=[CostEntry(component="c", cost=0.85)])

    alert = governor.check("career", journey)

    assert alert.level == BudgetAlertLevel.WARNING


def test_check_returns_exceeded_over_budget():
    governor = CostGovernor({"career": CostBudget(scope="career", limit=1.0)})
    journey = JourneyCost(journey="j", entries=[CostEntry(component="c", cost=1.5)])

    alert = governor.check("career", journey)

    assert alert.level == BudgetAlertLevel.EXCEEDED


def test_check_unknown_scope_raises():
    governor = CostGovernor({})
    journey = JourneyCost(journey="j", entries=[])

    with pytest.raises(ValueError):
        governor.check("unknown", journey)


def test_would_exceed_true_when_additional_cost_pushes_over():
    governor = CostGovernor({"career": CostBudget(scope="career", limit=1.0)})
    journey = JourneyCost(journey="j", entries=[CostEntry(component="c", cost=0.9)])

    assert governor.would_exceed("career", journey, additional_cost=0.2) is True


def test_would_exceed_false_when_still_under_budget():
    governor = CostGovernor({"career": CostBudget(scope="career", limit=1.0)})
    journey = JourneyCost(journey="j", entries=[CostEntry(component="c", cost=0.1)])

    assert governor.would_exceed("career", journey, additional_cost=0.2) is False
