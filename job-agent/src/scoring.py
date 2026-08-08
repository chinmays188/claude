import json
import os
import sqlite3

import anthropic
from dotenv import load_dotenv

from discovery import load_target_profile
from state import DB_PATH, ROOT

load_dotenv(ROOT / "config" / ".env", override=True)

MODEL = "claude-sonnet-5"

SCORING_PROMPT = """You are screening a job description against a candidate's target profile.
Score relevance from 0.0 to 1.0 based on role/title match, domain match, seniority/experience fit,
and any excluded companies/industries (score 0.0 if excluded).

Target profile:
{profile}

Job:
Title: {title}
Company: {company}
Location: {location}
Description: {jd_text}

Respond with ONLY a JSON object: {{"score": <float 0-1>, "reason": "<one sentence>"}}
"""


def score_job(client, profile, job):
    prompt = SCORING_PROMPT.format(
        profile=json.dumps(profile),
        title=job["title"],
        company=job["company"],
        location=job["location"],
        jd_text=(job["jd_text"] or "")[:4000],
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next(b.text for b in response.content if hasattr(b, "text")).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
        text = text.strip()
    try:
        result = json.loads(text)
        return float(result["score"]), result.get("reason", "")
    except (json.JSONDecodeError, KeyError, ValueError):
        return 0.0, f"unparseable scorer response: {text[:200]}"


def run_scoring():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set — add it to config/.env")

    client = anthropic.Anthropic(api_key=api_key)
    profile = load_target_profile()
    threshold = profile.get("relevance_threshold", 0.7)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM jobs WHERE status = 'new'").fetchall()

    scored, rejected = [], []
    for row in rows:
        job = dict(row)
        score, reason = score_job(client, profile, job)
        new_status = "scored" if score >= threshold else "rejected"
        conn.execute(
            "UPDATE jobs SET relevance_score = ?, status = ? WHERE id = ?",
            (score, new_status, job["id"]),
        )
        conn.commit()
        (scored if new_status == "scored" else rejected).append((job["id"], score, reason))

    conn.close()
    return scored, rejected


if __name__ == "__main__":
    scored, rejected = run_scoring()
    print(f"Scored: {len(scored)} passed threshold, {len(rejected)} rejected.")
