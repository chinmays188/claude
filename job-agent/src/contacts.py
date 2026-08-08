import asyncio
import re
import sqlite3

from mcp_linkedin_client import LinkedInMCPClient
from state import DB_PATH, load_config, log_run, preflight, trigger_backoff, clear_backoff

PRIORITY_TITLE_HINTS = {
    "hiring_manager": ["manager", "lead", "head"],
    "recruiter_ta": ["recruit", "talent acquisition", "ta "],
    "same_title_peer": ["product manager"],
    "function_leadership": ["vp", "vice president", "director"],
}

_COMPANY_SLUG_RE = re.compile(r"/company/([^/?#]+)/?")
_PERSON_USERNAME_RE = re.compile(r"/in/([^/?#]+)/?")

# Employee cards on the /people/ page repeat as:
#   <Name>
#   [2nd degree connection / ...connection lines]
#   <Title>
#   [mutual connections line]
#   Connect|Follow
_CONNECTION_DEGREE_LINE = re.compile(r"connection|^[·•]?\s*\d+(st|nd|rd|th)$", re.IGNORECASE)
_MUTUAL_LINE = re.compile(r"mutual connection|is a mutual|followers", re.IGNORECASE)
_ACTION_LINE = re.compile(r"^(Connect|Follow|Message)$", re.IGNORECASE)


def classify_contact(title: str) -> str:
    title_lower = (title or "").lower()
    for category, hints in PRIORITY_TITLE_HINTS.items():
        if any(hint in title_lower for hint in hints):
            return category
    return "other"


def rank_contacts(employees: list, priority_order: list, max_contacts: int):
    ranked = []
    for category in priority_order:
        matches = [e for e in employees if classify_contact(e.get("title", "")) == category]
        ranked.extend(matches)
        if len(ranked) >= max_contacts:
            break
    return ranked[:max_contacts]


def insert_contact(conn, job_id, contact, rank):
    conn.execute(
        """INSERT INTO contacts (job_id, name, title, profile_url, rank, send_status)
           VALUES (?, ?, ?, ?, ?, 'draft')""",
        (job_id, contact.get("name"), contact.get("title"), contact.get("profile_url"), rank),
    )
    conn.commit()


def resolve_company_slug(search_result):
    """First company reference from search_companies() is the best-match page."""
    if not isinstance(search_result, dict):
        return None
    refs = search_result.get("references", {}).get("search_results", [])
    for ref in refs:
        if ref.get("kind") == "company":
            m = _COMPANY_SLUG_RE.search(ref.get("url", ""))
            if m:
                return m.group(1)
    return None


def parse_employee_titles(text):
    """Pull the title line that follows each name's connection-degree line(s)
    on the /people/ "People you may know" section, in DOM order."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    titles = []
    i = 0
    while i < len(lines):
        if _CONNECTION_DEGREE_LINE.search(lines[i]) and not _ACTION_LINE.match(lines[i]):
            j = i + 1
            while j < len(lines) and _CONNECTION_DEGREE_LINE.search(lines[j]):
                j += 1
            if j < len(lines) and not _MUTUAL_LINE.search(lines[j]) and not _ACTION_LINE.match(lines[j]):
                titles.append(lines[j])
            i = j
        else:
            i += 1
    return titles


def parse_employees(employees_result):
    """references["employees"] gives clean (name, username) pairs in DOM
    order; pair them positionally with titles parsed from the scraped text."""
    if not isinstance(employees_result, dict):
        return []
    refs = employees_result.get("references", {}).get("employees", [])
    person_refs = [r for r in refs if r.get("kind") == "person"]
    text = employees_result.get("sections", {}).get("employees", "")
    titles = parse_employee_titles(text)

    employees = []
    for ref, title in zip(person_refs, titles):
        m = _PERSON_USERNAME_RE.search(ref.get("url", ""))
        if not m:
            continue
        employees.append({
            "name": ref.get("text", ""),
            "title": title,
            "linkedin_username": m.group(1),
            "profile_url": f"https://www.linkedin.com/in/{m.group(1)}/",
        })
    return employees


async def run_contact_discovery():
    remaining_budget = preflight()
    config = load_config()
    max_contacts = config["max_contacts_per_company"]
    priority_order = config["contact_priority_order"]
    max_companies = config["max_companies_per_cycle"]

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    jobs = conn.execute("SELECT * FROM jobs WHERE status = 'tailored'").fetchall()

    calls_made = 0
    errors = None
    processed_companies = 0
    results = []

    try:
        async with LinkedInMCPClient() as client:
            for job in jobs:
                if processed_companies >= max_companies or client.calls_made >= remaining_budget:
                    break
                job = dict(job)

                search_result = await client.search_companies(keywords=job["company"])
                slug = resolve_company_slug(search_result)
                if not slug or client.calls_made >= remaining_budget:
                    continue

                employees_result = await client.get_company_employees(company_name=slug)
                employees = parse_employees(employees_result)
                ranked = rank_contacts(employees, priority_order, max_contacts)

                for i, person in enumerate(ranked, start=1):
                    if client.calls_made >= remaining_budget:
                        break
                    profile = await client.get_person_profile(linkedin_username=person["linkedin_username"])
                    person["detail"] = profile
                    insert_contact(conn, job["id"], person, i)

                processed_companies += 1
                results.append((job["id"], len(ranked)))
            calls_made = client.calls_made
        clear_backoff()
    except Exception as e:
        errors = str(e)
        trigger_backoff()
    finally:
        log_run(calls_made=calls_made, errors=errors)
        conn.close()

    return results, errors


if __name__ == "__main__":
    results, err = asyncio.run(run_contact_discovery())
    if err:
        print(f"Contact discovery ended with error (backoff triggered): {err}")
    else:
        print(f"Contact discovery complete for {len(results)} companies.")
