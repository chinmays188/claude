from datetime import datetime

from pydantic import BaseModel


class CalendarEvent(BaseModel):
    event_id: str
    title: str
    start: datetime
    end: datetime
    attendees: list[str] = []


class CalendarClient:
    """Stub calendar client per Section 24 — same read-only interface a real
    Google Calendar / Outlook integration would expose, but backed by
    caller-supplied fixed data instead of an OAuth-authenticated API. No write
    methods exist (Section 24: 'Do not initially modify calendar events.
    Read-only first.'), mirroring GitHubClient's read-only-only surface."""

    def __init__(self, events: list[CalendarEvent] | None = None):
        self._events = events or []

    def get_events(self, day: datetime) -> list[CalendarEvent]:
        return [e for e in self._events if e.start.date() == day.date()]

    def find_conflicts(self, day: datetime) -> list[tuple[CalendarEvent, CalendarEvent]]:
        events = sorted(self.get_events(day), key=lambda e: e.start)
        conflicts = []
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                if events[i].end > events[j].start:
                    conflicts.append((events[i], events[j]))
        return conflicts
