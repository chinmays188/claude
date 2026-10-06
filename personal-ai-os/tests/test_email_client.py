from datetime import datetime, timezone

import pytest

from app.integrations.email_client import Email, EmailClient

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _email(id_, subject="Hello") -> Email:
    return Email(email_id=id_, sender="a@b.com", subject=subject, body="body", received_at=NOW)


def test_send_email_adds_it():
    client = EmailClient()

    sent = client.send_email(_email("e1"))

    assert sent.email_id == "e1"
    assert client.get_emails(NOW, NOW) == [sent]


def test_recall_email_removes_it():
    client = EmailClient([_email("e1")])

    client.recall_email("e1")

    assert client.get_emails(NOW, NOW) == []


def test_recall_missing_email_raises():
    client = EmailClient()

    with pytest.raises(ValueError):
        client.recall_email("does-not-exist")
