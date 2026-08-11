from datetime import datetime
from enum import Enum

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
    """Stub email client per Section 25 — same read-only shape a real Gmail/
    Outlook integration would expose, backed by caller-supplied fixed data.
    Classification (Section 25's 5 categories) is a separate step
    (classify_email), not baked into fetching, since real inboxes don't arrive
    pre-labeled."""

    def __init__(self, emails: list[Email] | None = None):
        self._emails = emails or []

    def get_emails(self, since: datetime, until: datetime) -> list[Email]:
        return [e for e in self._emails if since <= e.received_at <= until]
