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
