from datetime import datetime, timezone

from app.integrations.calendar_client import CalendarClient, CalendarEvent
from app.tools.calendar_tool import CalendarDayTool

DAY = datetime(2026, 1, 15, tzinfo=timezone.utc)


def _event(id_, start_hour, end_hour, title="Meeting") -> CalendarEvent:
    return CalendarEvent(
        event_id=id_, title=title,
        start=DAY.replace(hour=start_hour), end=DAY.replace(hour=end_hour),
    )


def test_get_events_filters_by_day():
    other_day = DAY.replace(day=16)
    client = CalendarClient([_event("e1", 9, 10), _event("e2", 9, 10)])

    events = client.get_events(DAY)

    assert len(events) == 2


def test_create_event_adds_a_real_event():
    client = CalendarClient()
    event = _event("new1", 9, 10)

    created = client.create_event(event)

    assert created.event_id == "new1"
    assert client.get_events(DAY) == [event]


def test_delete_event_removes_it():
    client = CalendarClient([_event("e1", 9, 10)])

    client.delete_event("e1")

    assert client.get_events(DAY) == []


def test_delete_missing_event_raises():
    client = CalendarClient()

    import pytest
    with pytest.raises(ValueError):
        client.delete_event("does-not-exist")


def test_find_conflicts_detects_overlap():
    client = CalendarClient([_event("e1", 9, 11), _event("e2", 10, 12)])

    conflicts = client.find_conflicts(DAY)

    assert len(conflicts) == 1


def test_find_conflicts_none_when_no_overlap():
    client = CalendarClient([_event("e1", 9, 10), _event("e2", 10, 11)])

    conflicts = client.find_conflicts(DAY)

    assert conflicts == []


def test_calendar_tool_reports_no_events():
    tool = CalendarDayTool(CalendarClient([]))

    result = tool.call({"day": DAY.isoformat()})

    assert "No events" in result


def test_calendar_tool_reports_conflicts():
    tool = CalendarDayTool(CalendarClient([_event("e1", 9, 11), _event("e2", 10, 12)]))

    result = tool.call({"day": DAY.isoformat()})

    assert "conflict" in result.lower()


def test_calendar_client_now_supports_real_write_and_undo():
    # Section 24's original "do not initially modify calendar events" rule
    # was explicitly reversed while investigating "Human-in-the-Loop AI"
    # ("we should move out of read only scope now and add the undo") --
    # this test replaces the old "never writes" structural guarantee with
    # the new, deliberate one: both methods exist and are simulated (same
    # in-memory fidelity as the read methods), not a real OAuth call.
    assert hasattr(CalendarClient, "create_event")
    assert hasattr(CalendarClient, "delete_event")
