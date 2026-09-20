from datetime import date, datetime, timedelta, timezone

import pytest

from app.db.connection import get_connection
from app.domains.cross_domain.goal_store import GoalNotFoundError, GoalStore
from app.domains.cross_domain.models import Goal, GoalStatus
from app.domains.router import Domain


def _store() -> GoalStore:
    return GoalStore(get_connection(":memory:"))


def _goal(owner="alice", title="Get AI PM role", domain=Domain.CAREER, priority=0.8) -> Goal:
    return Goal(owner_id=owner, title=title, domain=domain, priority=priority)


def test_create_and_get():
    store = _store()
    goal = _goal()
    store.create(goal)

    result = store.get(goal.goal_id)

    assert result.title == "Get AI PM role"
    assert result.domain == Domain.CAREER


def test_get_missing_raises():
    store = _store()

    with pytest.raises(GoalNotFoundError):
        store.get("does-not-exist")


def test_list_by_owner_scoped_correctly():
    store = _store()
    store.create(_goal(owner="alice"))
    store.create(_goal(owner="bob"))

    results = store.list_by_owner("alice")

    assert len(results) == 1
    assert results[0].owner_id == "alice"


def test_update_progress_clamped_and_marks_complete_at_100_percent():
    store = _store()
    goal = _goal()
    store.create(goal)

    store.update_progress(goal.goal_id, 1.5)
    result = store.get(goal.goal_id)

    assert result.progress == 1.0
    assert result.status == GoalStatus.COMPLETED


def test_update_status():
    store = _store()
    goal = _goal()
    store.create(goal)

    store.update_status(goal.goal_id, GoalStatus.BLOCKED)

    assert store.get(goal.goal_id).status == GoalStatus.BLOCKED


def test_goal_survives_across_store_instances_with_same_connection():
    conn = get_connection(":memory:")
    store1 = GoalStore(conn)
    goal = _goal()
    store1.create(goal)

    store2 = GoalStore(conn)
    result = store2.get(goal.goal_id)

    assert result.goal_id == goal.goal_id
