import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.proactive.events import Event, EventType


class Signal(BaseModel):
    """A candidate 'something worth surfacing to the user' produced by a
    trigger rule. Distinct from an Event: an Event is raw data that happened;
    a Signal is a trigger's judgment that the event might matter."""

    signal_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    owner_id: str
    trigger_name: str
    title: str
    description: str
    source_event_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Trigger(ABC):
    """Milestone 30's trigger engine: a rule that watches for a specific event
    pattern and, if matched, emits a Signal. Deliberately simple/deterministic
    rules here (not LLM calls) — deciding "did event X happen" should be cheap
    and auditable; judgment about whether it's worth the user's attention is
    the Attention Engine's job (Milestone 31), not the trigger's."""

    name: str
    watches: EventType

    @abstractmethod
    def matches(self, event: Event) -> bool:
        """Return True if this event should produce a signal."""

    @abstractmethod
    def build_signal(self, event: Event) -> Signal:
        ...

    def evaluate(self, event: Event) -> Signal | None:
        if event.type != self.watches or not self.matches(event):
            return None
        return self.build_signal(event)


class TriggerEngine:
    def __init__(self, triggers: list[Trigger]):
        self._triggers = triggers

    def evaluate(self, event: Event) -> list[Signal]:
        signals = []
        for trigger in self._triggers:
            signal = trigger.evaluate(event)
            if signal is not None:
                signals.append(signal)
        return signals
