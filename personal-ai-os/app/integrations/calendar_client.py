import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class CalendarEvent(BaseModel):
    event_id: str
    title: str
    start: datetime
    end: datetime
    attendees: list[str] = []


class CalendarClient:
    """Stub calendar client — same interface a real Google Calendar /
    Outlook integration would expose, but backed by caller-supplied fixed
    data instead of an OAuth-authenticated API.

    HISTORY: originally read-only only, per Section 24's "do not initially
    modify calendar events" scope decision. That decision was explicitly
    reversed while investigating "Human-in-the-Loop AI" ("we should move
    out of read only scope now and add the undo") -- create_event/
    delete_event below are the real write+undo pair this reversal exists
    to demonstrate.

    A second real finding followed from the first: when a write-capable
    tool runs inside SandboxedToolExecutor, each call executes in a
    separate spawned process (app/platform/sandbox.py) -- a plain
    in-memory list mutation happens in a throwaway child and is invisible
    to the caller once that process exits. Fixed with an optional
    file_path: when given, every write is a real read-modify-write to a
    real JSON file on disk, so the write survives the process boundary
    the same way the SQLite-backed stores already do. Without file_path,
    this behaves exactly as before (in-memory only, for tests/fixtures
    that never cross a process boundary)."""

    def __init__(self, events: list[CalendarEvent] | None = None, file_path: str | None = None):
        self._file_path = Path(file_path) if file_path else None
        self._events = events or []
        if self._file_path is not None and not self._file_path.exists():
            self._write_file()

    def _read_events(self) -> list[CalendarEvent]:
        # Real fix for a real cross-process gap: when file_path is set,
        # every read re-reads the file instead of trusting self._events --
        # a sandboxed write lands on disk from inside a spawned child
        # process (see SandboxedToolExecutor), so the PARENT's in-memory
        # self._events goes stale the moment that child exits. Re-reading
        # here, not just in __init__, is what makes the write visible to
        # the caller that proposed it.
        if self._file_path is None:
            return self._events
        if not self._file_path.exists():
            return []
        return [CalendarEvent.model_validate(e) for e in json.loads(self._file_path.read_text())]

    def _write_file(self) -> None:
        if self._file_path is None:
            return
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps([e.model_dump(mode="json") for e in self._events]))

    def get_events(self, day: datetime) -> list[CalendarEvent]:
        return [e for e in self._read_events() if e.start.date() == day.date()]

    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        self._events = self._read_events()
        self._events.append(event)
        self._write_file()
        return event

    def delete_event(self, event_id: str) -> None:
        self._events = self._read_events()
        before = len(self._events)
        self._events = [e for e in self._events if e.event_id != event_id]
        if len(self._events) == before:
            raise ValueError(f"No calendar event with id '{event_id}'.")
        self._write_file()

    def find_conflicts(self, day: datetime) -> list[tuple[CalendarEvent, CalendarEvent]]:
        events = sorted(self.get_events(day), key=lambda e: e.start)
        conflicts = []
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                if events[i].end > events[j].start:
                    conflicts.append((events[i], events[j]))
        return conflicts
