import json
from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel


class EmailCategory(str, Enum):
    FYI = "FYI"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    WAITING_FOR_RESPONSE = "WAITING_FOR_RESPONSE"
    COMMITMENT = "COMMITMENT"
    URGENT = "URGENT"


class Email(BaseModel):
    email_id: str
    sender: str
    subject: str
    body: str
    received_at: datetime
    category: EmailCategory | None = None  # classified separately, not fetched pre-labeled


class EmailClient:
    """Stub email client — same shape a real Gmail/Outlook integration
    would expose, backed by caller-supplied fixed data. Classification
    (Section 25's 5 categories) is a separate step (classify_email), not
    baked into fetching, since real inboxes don't arrive pre-labeled.

    HISTORY: originally read-only only (Section 25). Explicitly reversed
    while investigating "Human-in-the-Loop AI" ("we should move out of
    read only scope now and add the undo") -- send_email/recall_email
    below are the real write+undo pair this exists to demonstrate.
    Deliberately simulated (no real SMTP/Gmail send -- no credentials are
    configured in this environment).

    A second real finding followed from the first, same as
    CalendarClient: a write-capable tool running inside
    SandboxedToolExecutor executes in a separate spawned process, so a
    plain in-memory mutation is invisible to the caller once that child
    exits. Fixed the same way: an optional file_path makes every write a
    real read-modify-write to a real JSON file, and every read re-reads
    that file rather than trusting self._emails, so a sandboxed write
    becomes visible to the caller that proposed it."""

    def __init__(self, emails: list[Email] | None = None, file_path: str | None = None):
        self._file_path = Path(file_path) if file_path else None
        self._emails = emails or []
        if self._file_path is not None and not self._file_path.exists():
            self._write_file()

    def _read_emails(self) -> list[Email]:
        if self._file_path is None:
            return self._emails
        if not self._file_path.exists():
            return []
        return [Email.model_validate(e) for e in json.loads(self._file_path.read_text())]

    def _write_file(self) -> None:
        if self._file_path is None:
            return
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_path.write_text(json.dumps([e.model_dump(mode="json") for e in self._emails]))

    def get_emails(self, since: datetime, until: datetime) -> list[Email]:
        return [e for e in self._read_emails() if since <= e.received_at <= until]

    def send_email(self, email: Email) -> Email:
        self._emails = self._read_emails()
        self._emails.append(email)
        self._write_file()
        return email

    def recall_email(self, email_id: str) -> None:
        """Real email providers only support recall in narrow cases (e.g.
        Outlook/Exchange same-org, often failing if already read) -- this
        simulated client always succeeds, since it isn't modeling that
        real-world unreliability, only the undo mechanism itself."""
        self._emails = self._read_emails()
        before = len(self._emails)
        self._emails = [e for e in self._emails if e.email_id != email_id]
        if len(self._emails) == before:
            raise ValueError(f"No email with id '{email_id}'.")
        self._write_file()
