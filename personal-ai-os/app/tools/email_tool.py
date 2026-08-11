from datetime import datetime

from pydantic import BaseModel

from app.integrations.email_classifier import classify_email
from app.integrations.email_client import EmailClient
from app.providers.base import LLMProvider
from app.tools.base import Tool


class EmailSummaryArgs(BaseModel):
    since: datetime
    until: datetime


class EmailSummaryTool(Tool):
    name = "email_summary"
    description = (
        "Fetch and classify emails within a date range into FYI, action required, "
        "waiting for response, commitment, or urgent. Use this for questions like "
        "'what important emails did I receive today?'"
    )
    args_schema = EmailSummaryArgs
    permissions = ["read:email"]
    retry_safe = True

    def __init__(self, client: EmailClient, llm: LLMProvider):
        self._client = client
        self._llm = llm

    def run(self, args: EmailSummaryArgs) -> str:
        emails = self._client.get_emails(args.since, args.until)
        if not emails:
            return "No emails found in this period."

        lines = []
        for email in emails:
            category = classify_email(self._llm, email)
            lines.append(f"- [{category.value}] {email.subject} (from {email.sender})")

        return "\n".join(lines)
