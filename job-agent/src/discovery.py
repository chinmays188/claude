import asyncio
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from mcp_linkedin_client import LinkedInMCPClient
from state import DB_PATH, ROOT, log_run, preflight, trigger_backoff, clear_backoff

CONFIG_PATH = ROOT / "config" / "target_profile.json"
AGENT_CONFIG_PATH = ROOT / "config" / "agent_config.json"

# Pilot phase runs the full pipeline once/day, so only jobs LinkedIn itself
# reports as posted in the last 24h are worth fetching — filtering server-side
# also avoids spending calls scraping jobs we'd discard anyway.
DATE_POSTED_FILTER = "past_24_hours"

# search_jobs/get_job_details return raw scraped page text, not structured
# fields. Job cards in "sections.search_results" repeat as:
#   <Title>
#   <Company>
#   <Location> (<On-site|Remote|Hybrid>)
#   [noise lines: Promoted, Easy Apply, Viewed, "N connections work here", ...]
_NOISE_LINE = re.compile(
    r"^(Promoted|Easy Apply|Viewed|Actively reviewing applicants|"
    r"\d+ (connection|company alum|school alum)s? works? here|"
    r"\d+\+? (day|week|month)s? ago|"
    r"Set alert|Set job alert|Jump to |Are (these|you)|"
    r"Your feedback|Achieve your career|Try now|Dismiss|"
    r"Company review time|Up to ₹|\d+$|Next$)",
    re.IGNORECASE,
)
_LOCATION_LINE = re.compile(r".+\((On-site|Remote|Hybrid)\)\s*$")


def load_target_profile():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def job_exists(conn, job_id):
    row = conn.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return row is not None


def insert_job(conn, job):
    conn.execute(
        """INSERT OR IGNORE INTO jobs
           (id, title, company, location, jd_text, posted_at, first_seen_at, job_url, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
        (
            job["id"],
            job["title"],
            job["company"],
            job.get("location"),
            job.get("jd_text"),
            job.get("posted_at"),
            datetime.now().isoformat(),
            f"https://www.linkedin.com/jobs/view/{job['id']}/",
        ),
    )
    conn.commit()


def parse_search_cards(text):
    """Parse job cards (title, company, location) out of scraped search-results
    text, in DOM order, to be zip()'d against the parallel job_ids list."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cards = []
    i = 0
    while i < len(lines) - 2:
        title, company, loc = lines[i], lines[i + 1], lines[i + 2]
        if (
            not _NOISE_LINE.match(title)
            and not _NOISE_LINE.match(company)
            and _LOCATION_LINE.match(loc)
        ):
            cards.append({"title": title, "company": company, "location": loc})
            i += 3
        else:
            i += 1
    return cards


async def run_discovery():
    remaining_budget = preflight()
    profile = load_target_profile()
    conn = sqlite3.connect(DB_PATH)
    calls_made = 0
    new_jobs = []
    errors = None

    try:
        async with LinkedInMCPClient() as client:
            for role in profile["roles"]:
                for location in profile["locations"]:
                    if client.calls_made >= remaining_budget:
                        break
                    result = await client.search_jobs(
                        keywords=role, location=location, date_posted=DATE_POSTED_FILTER,
                    )
                    if not isinstance(result, dict):
                        continue

                    job_ids = result.get("job_ids", [])
                    search_text = result.get("sections", {}).get("search_results", "")
                    cards = parse_search_cards(search_text)

                    for job_id, card in zip(job_ids, cards):
                        if job_exists(conn, job_id):
                            continue
                        if client.calls_made >= remaining_budget:
                            new_jobs.append({
                                "id": job_id, "title": card["title"],
                                "company": card["company"], "location": card["location"],
                                "pending_details": True,
                            })
                            continue
                        details = await client.get_job_details(job_id=job_id)
                        jd_text = (
                            details.get("sections", {}).get("job_posting", "")
                            if isinstance(details, dict) else str(details)
                        )
                        insert_job(conn, {
                            "id": job_id,
                            "title": card["title"],
                            "company": card["company"],
                            "location": card["location"],  # real scraped location, not the search term
                            "jd_text": jd_text,
                        })
                        new_jobs.append({"id": job_id, "title": card["title"]})
            calls_made = client.calls_made
        clear_backoff()
    except Exception as e:
        errors = str(e)
        trigger_backoff()
    finally:
        log_run(calls_made=calls_made, errors=errors)
        conn.close()

    return new_jobs, errors


if __name__ == "__main__":
    jobs, err = asyncio.run(run_discovery())
    if err:
        print(f"Discovery run ended with error (backoff triggered): {err}")
    else:
        print(f"Discovery complete. {len(jobs)} new jobs found.")
