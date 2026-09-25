from datetime import datetime, timedelta, timezone

from app.proactive.builtin_triggers import (
    GoalDeadlineApproachingTrigger,
    StalledGoalTrigger,
    TaskStuckTrigger,
    UrgentEmailTrigger,
)
from app.proactive.events import Event, EventType
from app.proactive.triggers import TriggerEngine


def test_task_stuck_trigger_fires_when_threshold_exceeded():
    trigger = TaskStuckTrigger(stuck_threshold_hours=24)
    event = Event(
        type=EventType.TASK_STATE_CHANGED, owner_id="alice",
        payload={"state": "RUNNING", "hours_in_state": 30, "title": "Research AI PM companies"},
    )

    signal = trigger.evaluate(event)

    assert signal is not None
    assert "Research AI PM companies" in signal.title


def test_task_stuck_trigger_does_not_fire_below_threshold():
    trigger = TaskStuckTrigger(stuck_threshold_hours=24)
    event = Event(type=EventType.TASK_STATE_CHANGED, owner_id="alice", payload={"state": "RUNNING", "hours_in_state": 5})

    assert trigger.evaluate(event) is None


def test_task_stuck_trigger_ignores_other_event_types():
    trigger = TaskStuckTrigger()
    event = Event(type=EventType.GOAL_UPDATED, owner_id="alice", payload={"state": "RUNNING", "hours_in_state": 100})

    assert trigger.evaluate(event) is None


def test_goal_deadline_trigger_fires_when_at_risk():
    trigger = GoalDeadlineApproachingTrigger(days_threshold=7, progress_threshold=0.7)
    event = Event(
        type=EventType.GOAL_UPDATED, owner_id="alice",
        payload={"days_remaining": 3, "progress": 0.4, "title": "Prepare for interviews"},
    )

    signal = trigger.evaluate(event)

    assert signal is not None
    assert "Prepare for interviews" in signal.title


def test_goal_deadline_trigger_does_not_fire_when_on_track():
    trigger = GoalDeadlineApproachingTrigger(days_threshold=7, progress_threshold=0.7)
    event = Event(type=EventType.GOAL_UPDATED, owner_id="alice", payload={"days_remaining": 3, "progress": 0.9})

    assert trigger.evaluate(event) is None


def test_goal_deadline_trigger_does_not_fire_without_deadline_data():
    trigger = GoalDeadlineApproachingTrigger()
    event = Event(type=EventType.GOAL_UPDATED, owner_id="alice", payload={"progress": 0.1})

    assert trigger.evaluate(event) is None


def test_urgent_email_trigger_fires_on_urgent_category():
    trigger = UrgentEmailTrigger()
    event = Event(type=EventType.EMAIL_RECEIVED, owner_id="alice", payload={"category": "URGENT", "subject": "Server down"})

    signal = trigger.evaluate(event)

    assert signal is not None
    assert "Server down" in signal.title


def test_urgent_email_trigger_ignores_non_urgent():
    trigger = UrgentEmailTrigger()
    event = Event(type=EventType.EMAIL_RECEIVED, owner_id="alice", payload={"category": "FYI"})

    assert trigger.evaluate(event) is None


def test_trigger_engine_evaluates_all_triggers():
    engine = TriggerEngine([TaskStuckTrigger(), GoalDeadlineApproachingTrigger(), UrgentEmailTrigger()])
    event = Event(
        type=EventType.TASK_STATE_CHANGED, owner_id="alice",
        payload={"state": "WAITING", "hours_in_state": 48, "title": "Stuck task"},
    )

    signals = engine.evaluate(event)

    assert len(signals) == 1
    assert signals[0].trigger_name == "task_stuck"


def test_trigger_engine_returns_empty_list_when_nothing_matches():
    engine = TriggerEngine([TaskStuckTrigger(), UrgentEmailTrigger()])
    event = Event(type=EventType.TASK_STATE_CHANGED, owner_id="alice", payload={"state": "RUNNING", "hours_in_state": 1})

    assert engine.evaluate(event) == []


def test_stalled_goal_trigger_fires_for_deadline_less_stale_low_progress_goal():
    trigger = StalledGoalTrigger(staleness_days=7, progress_threshold=0.7)
    stale_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    event = Event(
        type=EventType.GOAL_UPDATED, owner_id="alice",
        payload={"days_remaining": None, "progress": 0.4, "title": "Multimodal AI", "updated_at": stale_time},
    )

    signal = trigger.evaluate(event)

    assert signal is not None
    assert "Multimodal AI" in signal.title


def test_stalled_goal_trigger_does_not_fire_when_recently_updated():
    trigger = StalledGoalTrigger(staleness_days=7, progress_threshold=0.7)
    recent_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    event = Event(
        type=EventType.GOAL_UPDATED, owner_id="alice",
        payload={"days_remaining": None, "progress": 0.4, "updated_at": recent_time},
    )

    assert trigger.evaluate(event) is None


def test_stalled_goal_trigger_does_not_fire_when_progress_is_high():
    trigger = StalledGoalTrigger(staleness_days=7, progress_threshold=0.7)
    stale_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    event = Event(
        type=EventType.GOAL_UPDATED, owner_id="alice",
        payload={"days_remaining": None, "progress": 0.85, "updated_at": stale_time},
    )

    assert trigger.evaluate(event) is None


def test_stalled_goal_trigger_defers_to_deadline_trigger_when_deadline_present():
    """A goal WITH a deadline is GoalDeadlineApproachingTrigger's job --
    StalledGoalTrigger must not also fire for it."""
    trigger = StalledGoalTrigger(staleness_days=7, progress_threshold=0.7)
    stale_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    event = Event(
        type=EventType.GOAL_UPDATED, owner_id="alice",
        payload={"days_remaining": 3, "progress": 0.4, "updated_at": stale_time},
    )

    assert trigger.evaluate(event) is None
