import sqlite3

from app.dashboard_ui.user_learning_goals import LEARNING_CAPABILITIES, seed_learning_capability_goals
from app.domains.cross_domain.goal_store import GoalStore
from app.domains.router import Domain


def _store():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return GoalStore(conn)


def test_seeds_exactly_15_capabilities():
    assert len(LEARNING_CAPABILITIES) == 15


def test_seed_creates_all_goals_as_learning_domain():
    store = _store()

    goals = seed_learning_capability_goals(store)

    assert len(goals) == 15
    assert all(g.domain == Domain.LEARNING for g in goals)


def test_seed_is_idempotent():
    store = _store()

    seed_learning_capability_goals(store)
    seed_learning_capability_goals(store)  # re-seed

    all_goals = store.list_by_owner("demo_user")
    assert len(all_goals) == 15  # no duplicates


def test_every_goal_has_success_criteria():
    store = _store()

    goals = seed_learning_capability_goals(store)

    assert all(len(g.success_criteria) > 0 for g in goals)


def test_goals_start_at_zero_progress_per_user_choice():
    """User explicitly chose defaults: progress=0.0, priority=0.5, no
    deadline -- to be updated later as their real learning progresses."""
    store = _store()

    goals = seed_learning_capability_goals(store)

    assert all(g.progress == 0.0 for g in goals)
    assert all(g.priority == 0.5 for g in goals)
    assert all(g.deadline is None for g in goals)
