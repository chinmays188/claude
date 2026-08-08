import json
import os
import sqlite3

import anthropic
from dotenv import load_dotenv

from contacts import classify_contact
from state import DB_PATH, ROOT
from tailoring import load_master_resume

load_dotenv(ROOT / "config" / ".env", override=True)

MODEL = "claude-sonnet-5"
MAX_WORDS = 300

TONE_BY_CATEGORY = {
    "hiring_manager": "technical and relevant to the role, show genuine understanding of the problem space",
    "recruiter_ta": "transactional, mention the specific req/role by name, concise",
    "same_title_peer": "informational and curious, ask about their experience rather than pitching yourself",
    "function_leadership": "brief and high-level, respectful of their time, no more than 3 sentences",
    "other": "polite, brief, and general",
}

DRAFT_PROMPT = """Draft a LinkedIn DM from the candidate to this contact, for a job outreach purpose.
Tone: {tone}

Hard requirements:
- No more than {max_words} words. Be direct, no filler or generic flattery.
- Identify the specific problem the company/role is trying to solve, based on the job description below.
- Connect that problem to 1-2 concrete pieces of the candidate's past experience (from their resume below)
  that show they can solve it — use real specifics (metrics, systems built), not vague claims.
- Do not invent experience or metrics not present in the candidate's resume.

Job description:
{jd_text}

Job: {title} at {company}
Contact: {contact_name}, {contact_title}

Candidate name: {candidate_name}
Candidate resume (JSON — headline, career_summary, and experience bullets):
{resume_json}

Sign off with the candidate's first name only. Return ONLY the message text, no preamble, no subject line.
"""


def draft_message(client, job, contact, master_resume):
    category = classify_contact(contact["title"])
    tone = TONE_BY_CATEGORY.get(category, TONE_BY_CATEGORY["other"])
    resume_summary = {
        "headline": master_resume["headline"],
        "career_summary": [b["text"] for b in master_resume["career_summary"]],
        "experience": [
            {"title": role["title"], "company": role["company"],
             "bullets": [b["text"] for b in role["bullets"]]}
            for role in master_resume["experience"]
        ],
    }
    prompt = DRAFT_PROMPT.format(
        tone=tone,
        max_words=MAX_WORDS,
        jd_text=(job.get("jd_text") or "")[:4000],
        title=job["title"],
        company=job["company"],
        contact_name=contact["name"],
        contact_title=contact["title"],
        candidate_name=master_resume["name"],
        resume_json=json.dumps(resume_summary),
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
    master_resume = load_master_resume()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    contacts = conn.execute(
        """SELECT contacts.*, jobs.title as job_title, jobs.company as job_company,
                  jobs.jd_text as job_jd_text
           FROM contacts JOIN jobs ON contacts.job_id = jobs.id
           WHERE contacts.message_draft IS NULL"""
    ).fetchall()

    drafted = 0
    for row in contacts:
        c = dict(row)
        job = {"title": c["job_title"], "company": c["job_company"], "jd_text": c["job_jd_text"]}
        contact = {"name": c["name"], "title": c["title"]}
        message = draft_message(client, job, contact, master_resume)
        conn.execute("UPDATE contacts SET message_draft = ? WHERE id = ?", (message, c["id"]))
        conn.commit()
        drafted += 1

    conn.close()
    return drafted


if __name__ == "__main__":
    n = run_outreach_drafting()
    print(f"Drafted {n} outreach messages.")
