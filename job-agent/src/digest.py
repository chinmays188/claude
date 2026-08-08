import smtplib
import sqlite3
from email.message import EmailMessage
from pathlib import Path

from state import DB_PATH, load_config, ROOT

# Human-readable fallback per contact_search_status, shown in the digest when
# no contacts were found — status alone ("no_contacts_found") doesn't tell
# the reader whether it's worth manually searching or a dead end.
_CONTACT_STATUS_EXPLANATIONS = {
    "not_attempted": "Contact search was not yet run for this job.",
    "company_unverified": "Could not confirm this company's LinkedIn page, so contact search was skipped.",
    "no_contacts_found": "Company was verified but no matching employees were found via LinkedIn.",
}


def build_digest_for_job(conn, job):
    contacts = conn.execute(
        "SELECT * FROM contacts WHERE job_id = ? ORDER BY rank", (job["id"],)
    ).fetchall()

    lines = [
        f"Job: {job['title']} at {job['company']} ({job['location']})",
        f"Job posting: {job['job_url']}",
        f"Relevance score: {job['relevance_score']:.2f}",
        f"Why this score: {job['relevance_reason'] or 'n/a'}",
        f"Posted: {job.get('posted_at', 'n/a')}",
        "",
    ]
    if contacts:
        lines.append("Ranked contacts and drafted outreach (nothing is sent until you approve each one):")
        lines.append("")
        for c in contacts:
            lines.append(f"{c['rank']}. {c['name']} — {c['title']}")
            lines.append(f"   Profile: {c['profile_url']}")
            lines.append(f"   Draft: {c['message_draft']}")
            lines.append("")
    else:
        explanation = _CONTACT_STATUS_EXPLANATIONS.get(
            job["contact_search_status"], job["contact_search_status"],
        )
        lines.append(f"No contacts found. Reason: {explanation}")
        lines.append("")

    tailored_resume = list((ROOT / "resume" / "tailored").glob(f"{job['id']}_*.pdf"))
    resume_path = str(tailored_resume[0]) if tailored_resume else None

    return "\n".join(lines), resume_path


def build_all_digests():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    jobs = conn.execute("SELECT * FROM jobs WHERE status = 'tailored'").fetchall()

    digests = []
    for row in jobs:
        job = dict(row)
        body, resume_path = build_digest_for_job(conn, job)
        digests.append({"job": job, "body": body, "resume_path": resume_path})

    conn.close()
    return digests


def send_digest_email(subject, body, resume_path, gmail_address, gmail_app_password, to_address):
    """SMTP send — only call this once Gmail app-password is configured (config/.env)."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = to_address
    msg.set_content(body)

    if resume_path and Path(resume_path).exists():
        with open(resume_path, "rb") as f:
            data = f.read()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="pdf",
            filename=Path(resume_path).name,
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_address, gmail_app_password)
        smtp.send_message(msg)


def mark_digested(job_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE jobs SET status = 'digested' WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    digests = build_all_digests()
    for d in digests:
        print(f"--- {d['job']['title']} @ {d['job']['company']} ---")
        print(d["body"])
