import json
import os
import re
import sqlite3

import anthropic
from dotenv import load_dotenv

from discovery import load_target_profile
from state import DB_PATH, ROOT

load_dotenv(ROOT / "config" / ".env", override=True)

MODEL = "claude-sonnet-5"
BATCH_SIZE = 8
MAX_TOKENS_PER_JOB = 400  # budget for each job's {score, reason} in a batched response
TOP_N = 10  # only the N highest-scored jobs move on to tailoring; the rest are rejected
AUTO_INCLUDE_FLOOR = 0.9  # score floor for auto-included jobs — a guarantee, not a fixed tie
AUTO_INCLUDE_GATE = 0.5  # floor only applies if the LLM's own score is at least this —
                          # prevents the floor from overriding a job the model has already
                          # correctly identified as irrelevant just because a keyword matched

SCORING_PROMPT = """You are screening job descriptions against a candidate's target profile.
Score each job's relevance from 0.0 to 1.0 based on role/title match, domain match, and
seniority/experience fit. Be discriminating: these scores will be used to rank jobs against
each other and select only the top {top_n}, so avoid clustering everything near the same score —
reserve 0.9+ for exceptional matches, and give a specific one-sentence reason that would let
someone compare two jobs' reasons and understand which is the better fit and why.

Target profile:
{profile}

Jobs to score:
{jobs_block}

Respond with ONLY a JSON array, one object per job in the same order, each shaped:
{{"index": <int, matching the job's index above>, "score": <float 0-1>, "reason": "<one sentence>"}}
"""

JOB_BLOCK_TEMPLATE = """[{index}] Title: {title}
Company: {company}
Location: {location}
Description: {jd_text}
"""


def strip_code_fence(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def is_excluded(profile, job):
    """Deterministic pre-check — skip the LLM entirely for a known-excluded
    company so exclusion never depends on the model reliably following an
    instruction, and no API call/cost is spent on it."""
    excluded_companies = {c.strip().lower() for c in profile.get("excluded_companies", [])}
    return (job["company"] or "").strip().lower() in excluded_companies


# Clear non-India location signals — deliberately conservative (reject only
# on a positive non-target match, not "doesn't contain a target city"),
# since scraped location text formatting is inconsistent and a false
# rejection is worse than letting the LLM's ranking down-weight a mismatch.
_NON_INDIA_LOCATION_RE = re.compile(
    r"united states|\busa\b|u\.s\.a?\.|remote\s*\(\s*us\s*\)|remote,?\s*us\b|"
    r"united kingdom|\buk\b|\bcanada\b|\bsingapore\b|\bgermany\b|\baustralia\b|"
    r"\beurope\b|\bemea\b|apac remote",
    re.IGNORECASE,
)


def is_location_excluded(job):
    """Deterministic pre-check — a job whose scraped location clearly
    indicates it's outside India never reaches scoring, regardless of how
    well title/domain match. Complements is_excluded (company) the same
    way: don't rely on the LLM to reliably apply a hard constraint."""
    return bool(_NON_INDIA_LOCATION_RE.search(job.get("location") or ""))


def is_auto_included(profile, job):
    """Job titles/descriptions matching auto_include_keywords (e.g. agentic
    AI, AI, CX) are guaranteed a high score floor — but still get scored by
    the LLM (not skipped), since with only TOP_N slots available we need a
    real, comparable score to rank auto-included jobs against each other and
    against everything else, not an artificial tie at a fixed value."""
    keywords = profile.get("auto_include_keywords", [])
    if not keywords:
        return False
    haystack = f"{job['title'] or ''} {job['jd_text'] or ''}"
    return any(re.search(pattern, haystack, re.IGNORECASE) for pattern in keywords)


def score_batch(client, profile, jobs):
    jobs_block = "\n".join(
        JOB_BLOCK_TEMPLATE.format(
            index=i, title=j["title"], company=j["company"],
            location=j["location"], jd_text=(j["jd_text"] or "")[:3000],
        )
        for i, j in enumerate(jobs)
    )
    prompt = SCORING_PROMPT.format(profile=json.dumps(profile), jobs_block=jobs_block, top_n=TOP_N)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS_PER_JOB * len(jobs),
        messages=[{"role": "user", "content": prompt}],
    )
    text_block = next((b.text for b in response.content if hasattr(b, "text")), None)
    if text_block is None:
        # No text block at all (e.g. max_tokens exhausted by extended
        # thinking before any output) — treat like any other unparseable
        # response so it's retried, not crashed.
        return {i: (None, "empty scorer response (no text block)") for i in range(len(jobs))}
    text = strip_code_fence(text_block.strip())

    try:
        results = json.loads(text)
        by_index = {int(r["index"]): (float(r["score"]), r.get("reason", "")) for r in results}
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        # Whole-batch parse failure — every job in this batch is marked as a
        # scoring failure (not a rejection) so it's retried on the next run
        # instead of silently treated as "not relevant".
        return {i: (None, f"unparseable scorer response: {text[:200]}") for i in range(len(jobs))}

    return {i: by_index.get(i, (None, "missing from scorer response")) for i in range(len(jobs))}


def run_scoring():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set — add it to config/.env")

    client = anthropic.Anthropic(api_key=api_key)
    profile = load_target_profile()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM jobs WHERE status IN ('new', 'scoring_failed')").fetchall()
    jobs = [dict(row) for row in rows]

    rejected, failed = [], []

    # Deterministic exclusion pass — no API call spent, never eligible for top-N.
    after_exclusion = []
    for job in jobs:
        if is_excluded(profile, job):
            conn.execute(
                "UPDATE jobs SET relevance_score = ?, relevance_reason = ?, status = ? WHERE id = ?",
                (0.0, "company is in excluded_companies", "rejected", job["id"]),
            )
            rejected.append((job["id"], 0.0, "excluded company"))
        elif is_location_excluded(job):
            conn.execute(
                "UPDATE jobs SET relevance_score = ?, relevance_reason = ?, status = ? WHERE id = ?",
                (0.0, f"location outside target region: {job.get('location')}", "rejected", job["id"]),
            )
            rejected.append((job["id"], 0.0, "excluded location"))
        else:
            after_exclusion.append(job)
    conn.commit()

    # Every remaining job gets a real LLM score — auto-include only raises a
    # floor afterward, it no longer skips scoring (needed so auto-included
    # jobs can still be ranked against each other for the top-N cut).
    candidates = []  # (job, score, reason) for everything that isn't excluded/failed
    for start in range(0, len(after_exclusion), BATCH_SIZE):
        batch = after_exclusion[start:start + BATCH_SIZE]
        results = score_batch(client, profile, batch)
        for i, job in enumerate(batch):
            score, reason = results[i]
            if score is None:
                failed.append((job["id"], reason))
                conn.execute(
                    "UPDATE jobs SET relevance_score = NULL, relevance_reason = ?, status = 'scoring_failed' WHERE id = ?",
                    (reason, job["id"]),
                )
                continue
            if is_auto_included(profile, job) and AUTO_INCLUDE_GATE <= score < AUTO_INCLUDE_FLOOR:
                score = AUTO_INCLUDE_FLOOR
                reason = f"{reason} (auto-include floor applied: matches an auto_include_keyword)"
            candidates.append((job, score, reason))
    conn.commit()

    # Rank everything that made it through scoring; only the top N move on.
    candidates.sort(key=lambda c: c[1], reverse=True)
    top = candidates[:TOP_N]
    rest = candidates[TOP_N:]

    scored = []
    for job, score, reason in top:
        conn.execute(
            "UPDATE jobs SET relevance_score = ?, relevance_reason = ?, status = 'scored' WHERE id = ?",
            (score, reason, job["id"]),
        )
        scored.append((job["id"], score, reason))
    for job, score, reason in rest:
        reason = f"{reason} (ranked outside top {TOP_N})"
        conn.execute(
            "UPDATE jobs SET relevance_score = ?, relevance_reason = ?, status = 'rejected' WHERE id = ?",
            (score, reason, job["id"]),
        )
        rejected.append((job["id"], score, reason))
    conn.commit()

    conn.close()
    return scored, rejected, failed


if __name__ == "__main__":
    scored, rejected, failed = run_scoring()
    print(f"Scored: {len(scored)} passed (top {TOP_N}), {len(rejected)} rejected, {len(failed)} failed to score.")
