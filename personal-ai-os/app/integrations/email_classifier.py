from pydantic import BaseModel

from app.integrations.email_client import Email, EmailCategory
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

CLASSIFY_PROMPT = """Classify this email into exactly one category.

Categories:
- FYI: informational only, no action needed
- ACTION_REQUIRED: the recipient needs to do something
- WAITING_FOR_RESPONSE: the recipient is waiting on someone else to respond
- COMMITMENT: the recipient has committed to doing something by a deadline
- URGENT: time-sensitive, needs immediate attention

From: {sender}
Subject: {subject}
Body: {body}

Respond with ONLY a JSON object:
{{"category": "FYI" | "ACTION_REQUIRED" | "WAITING_FOR_RESPONSE" | "COMMITMENT" | "URGENT"}}
"""


class _CategoryResult(BaseModel):
    category: EmailCategory


def classify_email(llm: LLMProvider, email: Email) -> EmailCategory:
    generator = RepairableGenerator(llm, _CategoryResult)
    prompt = CLASSIFY_PROMPT.format(sender=email.sender, subject=email.subject, body=email.body)
    result = generator.generate(prompt)
    return result.category
