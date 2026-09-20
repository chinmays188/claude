from app.dashboard.domain_data import (
    get_career_dashboard,
    get_finance_dashboard,
    get_learning_dashboard,
    get_pm_dashboard,
)
from app.db.connection import get_connection
from app.domains.cross_domain.goal_store import GoalStore
from app.domains.cross_domain.models import Goal
from app.domains.router import Domain


def _goal_store() -> GoalStore:
    return GoalStore(get_connection(":memory:"))


def test_career_dashboard_counts_career_goals():
    store = _goal_store()
    store.create(Goal(owner_id="alice", title="Get AI PM role", domain=Domain.CAREER))
    store.create(Goal(owner_id="alice", title="Learn Docker", domain=Domain.LEARNING))

    dashboard = get_career_dashboard(store, "alice", applications=3, resume_readiness=0.8)

    assert dashboard.career_goals_count == 1
    assert dashboard.applications == 3
    assert dashboard.resume_readiness == 0.8


def test_pm_dashboard_shapes_caller_supplied_data():
    dashboard = get_pm_dashboard(feedback_themes=["refund delays"], open_requests=5, sprint_status="on_track")

    assert dashboard.feedback_themes == ["refund delays"]
    assert dashboard.sprint_status == "on_track"


def test_finance_dashboard_counts_finance_goals():
    store = _goal_store()
    store.create(Goal(owner_id="alice", title="Retirement fund", domain=Domain.FINANCE))

    dashboard = get_finance_dashboard(store, "alice", portfolio_value=17000.0, allocation={"equity": 0.7, "debt": 0.3})

    assert dashboard.goals_count == 1
    assert dashboard.portfolio_value == 17000.0
    assert dashboard.allocation["equity"] == 0.7


def test_learning_dashboard_counts_learning_goals():
    store = _goal_store()
    store.create(Goal(owner_id="alice", title="Master Kubernetes", domain=Domain.LEARNING))

    dashboard = get_learning_dashboard(store, "alice", current_subjects=["Docker", "Kubernetes"], progress={"Docker": 8.0})

    assert dashboard.learning_goals_count == 1
    assert dashboard.progress["Docker"] == 8.0


def test_dashboards_default_gracefully_with_no_data():
    store = _goal_store()

    career = get_career_dashboard(store, "alice")
    pm = get_pm_dashboard()
    finance = get_finance_dashboard(store, "alice")
    learning = get_learning_dashboard(store, "alice")

    assert career.career_goals_count == 0
    assert pm.feedback_themes == []
    assert finance.goals_count == 0
    assert learning.learning_goals_count == 0
