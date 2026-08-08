import os
import sqlite3

import anthropic
from dotenv import load_dotenv

from contacts import classify_contact
from state import DB_PATH, ROOT

load_dotenv(ROOT / "config" / ".env", override=True)

MODEL = "claude-sonnet-5"

TONE_BY_CATEGORY = {
    "hiring_manager": "technical and relevant to the role, show genuine understanding of the problem space",
    "recruiter_ta": "transactional, mention the specific req/role by name, concise",
    "same_title_peer": "informational and curious, ask about their experience rather than pitching yourself",
    "function_leadership": "brief and high-level, respectful of their time, no more than 3 sentences",
    "other": "polite, brief, and general",
}

DRAFT_PROMPT = """Draft a short LinkedIn DM from the candidate to this contact, for a job outreach purpose.
Tone: {tone}
Keep it under 500 characters. No generic flattery. Reference the specific job and company naturally.

Candidate summary: AI Product Manager with 5+ years in conversational AI, voice AI, and customer experience.
Job: {title} at {company}
Contact: {contact_name}, {contact_title}

Return ONLY the message text, no preamble.
"""


def draft_message(client, job, contact):
    category = classify_contact(contact["title"])
    tone = TONE_BY_CATEGORY.get(category, TONE_BY_CATEGORY["other"])
    prompt = DRAFT_PROMPT.format(
        tone=tone,
        title=job["title"],
        company=job["company"],
        contact_name=contact["name"],
        contact_title=contact["title"],
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return next(b.text for b in response.content if hasattr(b, "text")).strip()


def run_outreach_drafting():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set — add it to config/.env")

    client = anthropic.Anthropic(api_key=api_key)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    contacts = conn.execute(
        """SELECT contacts.*, jobs.title as job_title, jobs.company as job_company
           FROM contacts JOIN jobs ON contacts.job_id = jobs.id
           WHERE contacts.message_draft IS NULL"""
    ).fetchall()

    drafted = 0
    for row in contacts:
        c = dict(row)
        job = {"title": c["job_title"], "company": c["job_company"]}
        contact = {"name": c["name"], "title": c["title"]}
        message = draft_message(client, job, contact)
        conn.execute("UPDATE contacts SET message_draft = ? WHERE id = ?", (message, c["id"]))
        conn.commit()
        drafted += 1

    conn.close()
    return drafted


if __name__ == "__main__":
    n = run_outreach_drafting()
    print(f"Drafted {n} outreach messages.")
