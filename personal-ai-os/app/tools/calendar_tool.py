from datetime import datetime

from pydantic import BaseModel

from app.integrations.calendar_client import CalendarClient
from app.tools.base import Tool


class CalendarDayArgs(BaseModel):
    day: datetime


class CalendarDayTool(Tool):
    name = "calendar_day"
    description = "Look up meetings, events, and scheduling conflicts for a given day."
    args_schema = CalendarDayArgs
    permissions = ["read:calendar"]
    retry_safe = True

    def __init__(self, client: CalendarClient):
        self._client = client

    def run(self, args: CalendarDayArgs) -> str:
        events = self._client.get_events(args.day)
        conflicts = self._client.find_conflicts(args.day)

        if not events:
            return f"No events scheduled for {args.day.date()}."

        lines = [f"Events on {args.day.date()}:"]
        for e in events:
            lines.append(f"- {e.start.strftime('%H:%M')}-{e.end.strftime('%H:%M')} {e.title}")

        if conflicts:
            lines.append(f"\n{len(conflicts)} scheduling conflict(s) detected.")

        return "\n".join(lines)
