from datetime import date

from app.db.connection import get_connection
from app.domains.cross_domain.goal_agent import GoalAgent
from app.domains.cross_domain.goal_store import GoalStore
from app.domains.cross_domain.models import Goal
from app.domains.router import Domain
from app.proactive.events import EventType
from app.proactive.goal_monitor import GoalMonitor
from app.proactive.triggers import TriggerEngine
from app.proactive.builtin_triggers import GoalDeadlineApproachingTrigger


def _monitor() -> GoalMonitor:
    store = GoalStore(get_connection(":memory:"))
    agent = GoalAgent(store)
    return GoalMonitor(agent), store


def test_check_goals_produces_goal_updated_events():
    monitor, store = _monitor()
    store.create(Goal(owner_id="alice", title="Learn Docker", domain=Domain.LEARNING, deadline=date(2026, 2, 1), progress=0.3))

    events = monitor.check_goals("alice", as_of=date(2026, 1, 25))

    assert len(events) == 1
    assert events[0].type == EventType.GOAL_UPDATED
    assert events[0].payload["days_remaining"] == 7
    assert events[0].payload["progress"] == 0.3


def test_check_goals_includes_domain_in_payload():
    monitor, store = _monitor()
    store.create(Goal(owner_id="alice", title="Career goal", domain=Domain.CAREER, deadline=date(2026, 2, 1)))

    events = monitor.check_goals("alice", as_of=date(2026, 1, 25))

    assert events[0].payload["domain"] == "CAREER"


def test_check_goals_handles_no_deadline():
    monitor, store = _monitor()
    store.create(Goal(owner_id="alice", title="Someday goal", domain=Domain.LEARNING, deadline=None))

    events = monitor.check_goals("alice")

    assert events[0].payload["days_remaining"] is None


def test_check_goals_integrates_with_trigger_engine():
    monitor, store = _monitor()
    store.create(Goal(owner_id="alice", title="At-risk goal", domain=Domain.CAREER, deadline=date(2026, 2, 1), progress=0.2))
    engine = TriggerEngine([GoalDeadlineApproachingTrigger(days_threshold=7, progress_threshold=0.7)])

    events = monitor.check_goals("alice", as_of=date(2026, 1, 28))
    all_signals = [s for event in events for s in engine.evaluate(event)]

    assert len(all_signals) == 1
    assert "At-risk goal" in all_signals[0].title


def test_check_goals_excludes_completed_goals():
    monitor, store = _monitor()
    goal = Goal(owner_id="alice", title="Done goal", domain=Domain.LEARNING, deadline=date(2026, 2, 1))
    store.create(goal)
    from app.domains.cross_domain.models import GoalStatus
    store.update_status(goal.goal_id, GoalStatus.COMPLETED)

    events = monitor.check_goals("alice")

    assert events == []
