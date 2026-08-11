from datetime import datetime, timezone

from app.integrations.email_classifier import classify_email
from app.integrations.email_client import Email, EmailCategory, EmailClient
from app.providers.base import LLMProvider
from app.tools.email_tool import EmailSummaryTool

NOW = datetime(2026, 1, 15, tzinfo=timezone.utc)
SINCE = datetime(2026, 1, 1, tzinfo=timezone.utc)
UNTIL = datetime(2026, 1, 31, tzinfo=timezone.utc)


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _email(id_="e1", subject="Test") -> Email:
    return Email(email_id=id_, sender="boss@company.com", subject=subject, body="Please review this by Friday.", received_at=NOW)


def test_get_emails_filters_by_date_range():
    out_of_range = _email("e2").model_copy(update={"received_at": datetime(2025, 1, 1, tzinfo=timezone.utc)})
    client = EmailClient([_email("e1"), out_of_range])

    emails = client.get_emails(SINCE, UNTIL)

    assert len(emails) == 1
    assert emails[0].email_id == "e1"


def test_classify_email_returns_category():
    llm = ScriptedProvider(['{"category": "ACTION_REQUIRED"}'])

    category = classify_email(llm, _email())

    assert category == EmailCategory.ACTION_REQUIRED


def test_email_tool_classifies_all_fetched_emails():
    llm = ScriptedProvider(['{"category": "URGENT"}'])
    client = EmailClient([_email()])
    tool = EmailSummaryTool(client, llm)

    result = tool.call({"since": SINCE.isoformat(), "until": UNTIL.isoformat()})

    assert "URGENT" in result


def test_email_tool_reports_no_emails():
    llm = ScriptedProvider([])
    tool = EmailSummaryTool(EmailClient([]), llm)

    result = tool.call({"since": SINCE.isoformat(), "until": UNTIL.isoformat()})

    assert "No emails" in result


def test_email_client_never_writes():
    assert not hasattr(EmailClient, "send_email")
    assert not hasattr(EmailClient, "delete_email")
