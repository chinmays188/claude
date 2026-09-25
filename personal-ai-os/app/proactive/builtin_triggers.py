from datetime import datetime, timezone

from app.proactive.events import Event, EventType
from app.proactive.triggers import Signal, Trigger


class TaskStuckTrigger(Trigger):
    """Fires when a task event's payload reports it's been RUNNING/WAITING
    without progress for too long. Reuses Phase 2's TaskState vocabulary via
    the payload rather than importing TaskStore directly, keeping this
    trigger decoupled from persistence."""

    name = "task_stuck"
    watches = EventType.TASK_STATE_CHANGED

    def __init__(self, stuck_threshold_hours: float = 24.0):
        self._threshold = stuck_threshold_hours

    def matches(self, event: Event) -> bool:
        state = event.payload.get("state")
        hours_in_state = event.payload.get("hours_in_state", 0)
        return state in ("RUNNING", "WAITING") and hours_in_state >= self._threshold

    def build_signal(self, event: Event) -> Signal:
        task_title = event.payload.get("title", "a task")
        hours = event.payload.get("hours_in_state", 0)
        return Signal(
            owner_id=event.owner_id, trigger_name=self.name,
            title=f"Task stuck: {task_title}",
            description=f"'{task_title}' has been in state '{event.payload.get('state')}' for {hours:.0f}h.",
            source_event_id=event.event_id,
        )


class GoalDeadlineApproachingTrigger(Trigger):
    """Fires when a goal-updated event reports a deadline within N days and
    progress below a threshold — reuses Phase 3's Goal fields via payload."""

    name = "goal_deadline_approaching"
    watches = EventType.GOAL_UPDATED

    def __init__(self, days_threshold: int = 7, progress_threshold: float = 0.7):
        self._days_threshold = days_threshold
        self._progress_threshold = progress_threshold

    def matches(self, event: Event) -> bool:
        days_remaining = event.payload.get("days_remaining")
        progress = event.payload.get("progress", 1.0)
        if days_remaining is None:
            return False
        return days_remaining <= self._days_threshold and progress < self._progress_threshold

    def build_signal(self, event: Event) -> Signal:
        title = event.payload.get("title", "a goal")
        days = event.payload.get("days_remaining")
        progress = event.payload.get("progress", 0.0)
        return Signal(
            owner_id=event.owner_id, trigger_name=self.name,
            title=f"Goal at risk: {title}",
            description=f"'{title}' is due in {days} day(s) but only {progress:.0%} complete.",
            source_event_id=event.event_id,
        )


class UrgentEmailTrigger(Trigger):
    """Fires on an email event pre-classified as URGENT (reusing Phase 2's
    EmailCategory) — this trigger doesn't classify itself, it reacts to a
    classification already done upstream."""

    name = "urgent_email"
    watches = EventType.EMAIL_RECEIVED

    def matches(self, event: Event) -> bool:
        return event.payload.get("category") == "URGENT"

    def build_signal(self, event: Event) -> Signal:
        subject = event.payload.get("subject", "an email")
        sender = event.payload.get("sender", "unknown sender")
        return Signal(
            owner_id=event.owner_id, trigger_name=self.name,
            title=f"Urgent email: {subject}",
            description=f"From {sender}: '{subject}' was classified as urgent.",
            source_event_id=event.event_id,
        )


class StalledGoalTrigger(Trigger):
    """Fires on a goal that has NO deadline (so GoalDeadlineApproachingTrigger
    never fires for it -- deliberately, since it only ever evaluates
    deadline proximity) but hasn't been updated in staleness_days and is
    still below progress_threshold. Built specifically for the user's
    15 real learning-capability goals, which were deliberately seeded with
    no deadline. Reuses the same GOAL_UPDATED event GoalMonitor already
    produces -- goal.updated_at is now included in that event's payload
    for exactly this purpose."""

    name = "goal_stalled_no_deadline"
    watches = EventType.GOAL_UPDATED

    def __init__(self, staleness_days: int = 7, progress_threshold: float = 0.7):
        self._staleness_days = staleness_days
        self._progress_threshold = progress_threshold

    def matches(self, event: Event) -> bool:
        if event.payload.get("days_remaining") is not None:
            return False  # has a deadline -- GoalDeadlineApproachingTrigger's job, not this one's
        progress = event.payload.get("progress", 1.0)
        if progress >= self._progress_threshold:
            return False
        updated_at_raw = event.payload.get("updated_at")
        if not updated_at_raw:
            return False
        updated_at = datetime.fromisoformat(updated_at_raw)
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - updated_at).total_seconds() / 86400
        return age_days >= self._staleness_days

    def build_signal(self, event: Event) -> Signal:
        title = event.payload.get("title", "a goal")
        progress = event.payload.get("progress", 0.0)
        return Signal(
            owner_id=event.owner_id, trigger_name=self.name,
            title=f"Goal stalled: {title}",
            description=f"'{title}' has no deadline but is only {progress:.0%} complete "
                         f"and hasn't been updated recently.",
            source_event_id=event.event_id,
        )
