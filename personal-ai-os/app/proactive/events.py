import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event sources per Phase 4's core concept list. Deliberately maps onto
    things this project can already produce (Phase 2 integrations, Phase 3
    domain agents) rather than inventing new event sources with no real
    producer behind them."""

    GITHUB_ACTIVITY = "github_activity"
    CALENDAR_EVENT = "calendar_event"
    EMAIL_RECEIVED = "email_received"
    TASK_STATE_CHANGED = "task_state_changed"
    GOAL_UPDATED = "goal_updated"
    DECISION_RECORDED = "decision_recorded"
    COMMITMENT_DETECTED = "commitment_detected"
    MEMORY_WRITTEN = "memory_written"


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    type: EventType
    owner_id: str
    payload: dict
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""  # e.g. "github_client", "calendar_client", "task_store"


class EventBus:
    """Milestone 30: a simple in-process pub/sub bus. Events are fed in
    explicitly (by a caller — a test, a manual poll, a Phase 2 integration
    result) rather than sourced from an always-on background poller, per
    project scope decision — this sandbox has no long-lived process to host
    real continuous polling."""

    def __init__(self):
        self._subscribers: dict[EventType, list] = {}
        self._history: list[Event] = []

    def subscribe(self, event_type: EventType, handler) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: Event) -> None:
        self._history.append(event)
        for handler in self._subscribers.get(event.type, []):
            handler(event)

    def history(self, owner_id: str | None = None) -> list[Event]:
        if owner_id is None:
            return list(self._history)
        return [e for e in self._history if e.owner_id == owner_id]
