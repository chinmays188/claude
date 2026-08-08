import asyncio
import re
import sqlite3

from mcp_linkedin_client import LinkedInMCPClient
from state import DB_PATH, load_config, log_run, preflight, trigger_backoff, clear_backoff

# Checked in this order — more specific phrases (e.g. "product manager")
# must be checked before generic ones ("manager") they're a substring of,
# or the generic hint always wins and the specific category is unreachable.
PRIORITY_TITLE_HINTS = {
    "same_title_peer": ["product manager"],
    "recruiter_ta": ["recruit", "talent acquisition", "ta "],
    "function_leadership": ["vp", "vice president", "director"],
    "hiring_manager": ["manager", "lead", "head"],
}

# Keywords that make a contact's title more relevant to *this specific job*,
# beyond just its category — same style of signal as scoring.py's
# auto_include_keywords, reused here to break ties within a category instead
# of taking whoever LinkedIn happened to list first.
_RELEVANCE_KEYWORDS = [
    r"\bai\b", "agentic", "conversational ai", "voice ai", r"\bcx\b",
    "customer experience", "product",
]

_COMPANY_SLUG_RE = re.compile(r"/company/([^/?#]+)/?")
_PERSON_USERNAME_RE = re.compile(r"/in/([^/?#]+)/?")

# Employee cards on the /people/ "People you may know" widget repeat as:
#   <Name>
#   [2nd degree connection / ...connection lines]
#   <Title>
#   [mutual connections line]
#   Connect|Follow
_CONNECTION_DEGREE_LINE = re.compile(r"connection|^[·•]?\s*\d+(st|nd|rd|th)$", re.IGNORECASE)
_MUTUAL_LINE = re.compile(r"mutual connection|is a mutual|followers", re.IGNORECASE)
_ACTION_LINE = re.compile(r"^(Connect|Follow|Message)$", re.IGNORECASE)

# search_people cards anchor on a "Current: <role> at <company>" line, which
# never appears for mutual-connection mentions swept into the same
# references list — the only reliable way to tell a real candidate card
# apart from a name-drop.
_CURRENT_LINE_RE = re.compile(r"^Current:\s*(.+?)\s+at\s+(.+)$", re.IGNORECASE)

# A parsed title that looks like noise rather than a real job title —
# guards against silently inserting garbage if LinkedIn's page layout shifts
# under the positional parser.
_NOISE_TITLE_RE = re.compile(
    r"^(connect|follow|message|\d+[\w\s]*followers?|past:|current:)",
    re.IGNORECASE,
)


def classify_contact(title: str) -> str:
    title_lower = (title or "").lower()
    for category, hints in PRIORITY_TITLE_HINTS.items():
        if any(hint in title_lower for hint in hints):
            return category
    return "other"


def is_valid_title(title, name):
    """Reject parsed titles that look like noise instead of a real job
    title — makes a LinkedIn layout change show up as fewer/skipped
    contacts (visible) rather than garbage titles inserted silently."""
    if not title or not title.strip():
        return False
    if title.strip().lower() == (name or "").strip().lower():
        return False
    if _NOISE_TITLE_RE.match(title.strip()):
        return False
    return True


def relevance_score(title):
    """Count of relevance keywords matched in a title — used to break ties
    within a priority category (e.g. prefer an 'AI Product Manager' title
    over a generic 'Product Manager' when both are same_title_peer)."""
    title_lower = (title or "").lower()
    return sum(1 for pattern in _RELEVANCE_KEYWORDS if re.search(pattern, title_lower))


def rank_contacts(people, priority_order, max_contacts):
    ranked = []
    for category in priority_order:
        matches = [p for p in people if classify_contact(p.get("title", "")) == category]
        matches.sort(key=lambda p: relevance_score(p.get("title", "")), reverse=True)
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


def _names_roughly_match(a, b):
    """Cheap fuzzy match for company display name vs. the name the job
    listing gave us — tolerant of suffixes like 'Inc'/'Ltd'/'India' and
    case, but still rejects an unrelated company."""
    def normalize(s):
        s = re.sub(r"\b(inc|ltd|india|pvt|limited|corp|corporation|technologies|tech)\b", "", s.lower())
        return re.sub(r"[^a-z0-9]", "", s)
    na, nb = normalize(a or ""), normalize(b or "")
    if not na or not nb:
        return False
    return na in nb or nb in na


def resolve_company_slug(search_result):
    """First company reference from search_companies() is the best-guess
    page — verified against the real company name in a later step via
    get_company_profile, since LinkedIn's own search ranking is not
    guaranteed to put the right company first (subsidiaries, similarly
    named companies)."""
    if not isinstance(search_result, dict):
        return None
    refs = search_result.get("references", {}).get("search_results", [])
    for ref in refs:
        if ref.get("kind") == "company":
            m = _COMPANY_SLUG_RE.search(ref.get("url", ""))
            if m:
                return m.group(1)
    return None


def verify_company_and_get_urn(profile_result, expected_company_name):
    """Returns (verified: bool, company_urn: str | None). Checks the
    resolved slug's About page against the job's company name before
    trusting it for employee/contact lookups — and extracts the numeric
    company URN (needed for search_people's current_company filter) along
    the way, since both come from the same call."""
    if not isinstance(profile_result, dict):
        return False, None
    about_text = profile_result.get("sections", {}).get("about", "")
    first_line = next((ln.strip() for ln in about_text.splitlines() if ln.strip()), "")
    verified = _names_roughly_match(first_line, expected_company_name)

    urn = None
    for ref in profile_result.get("references", {}).get("about", []):
        if ref.get("kind") == "company_urn":
            urn = ref.get("value")
            break
    return verified, urn


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


def parse_employees_from_widget(employees_result):
    """references["employees"] gives clean (name, username) pairs in DOM
    order; pair them positionally with titles parsed from the scraped text.
    This is LinkedIn's "People you may know" widget, not a full employee
    directory — coverage is inherently spotty (0 results is common)."""
    if not isinstance(employees_result, dict):
        return []
    refs = employees_result.get("references", {}).get("employees", [])
    person_refs = [r for r in refs if r.get("kind") == "person"]
    text = employees_result.get("sections", {}).get("employees", "")
    titles = parse_employee_titles(text)

    people = []
    for ref, title in zip(person_refs, titles):
        if not is_valid_title(title, ref.get("text", "")):
            continue
        m = _PERSON_USERNAME_RE.search(ref.get("url", ""))
        if not m:
            continue
        people.append({
            "name": ref.get("text", ""),
            "title": title,
            "linkedin_username": m.group(1),
            "profile_url": f"https://www.linkedin.com/in/{m.group(1)}/",
        })
    return people


def parse_people_from_search(search_result):
    """search_people results mix real candidate cards with mutual-connection
    name-drops in the same references list — anchor on each card's
    "Current: <role> at <company>" line (unique to real candidates) to tell
    them apart, and use that line as the title since it's a real job title,
    not the free-text headline tagline above it."""
    if not isinstance(search_result, dict):
        return []
    text = search_result.get("sections", {}).get("search_results", "")
    refs = search_result.get("references", {}).get("search_results", [])
    person_by_name = {}
    for ref in refs:
        if ref.get("kind") == "person":
            m = _PERSON_USERNAME_RE.search(ref.get("url", ""))
            if m:
                person_by_name.setdefault(ref.get("text", ""), m.group(1))

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    people = []
    current_name = None
    for line in lines:
        m = _CURRENT_LINE_RE.match(line)
        if m:
            title, company = m.group(1).strip(), m.group(2).strip()
            if current_name and is_valid_title(title, current_name):
                username = person_by_name.get(current_name)
                if username:
                    people.append({
                        "name": current_name,
                        "title": f"{title} at {company}",
                        "linkedin_username": username,
                        "profile_url": f"https://www.linkedin.com/in/{username}/",
                    })
            current_name = None
        elif line in person_by_name:
            current_name = line
    return people


async def find_company_contacts(client, job, remaining_budget):
    """Resolve + verify the company, then try the People-you-may-know widget
    first (cheap) and fall back to search_people (broader coverage, needs
    the company URN) if the widget returns nothing."""
    search_result = await client.search_companies(keywords=job["company"])
    slug = resolve_company_slug(search_result)
    if not slug or client.calls_made >= remaining_budget:
        return []

    profile_result = await client.get_company_profile(company_name=slug)
    verified, urn = verify_company_and_get_urn(profile_result, job["company"])
    if not verified or client.calls_made >= remaining_budget:
        return []

    employees_result = await client.get_company_employees(company_name=slug)
    people = parse_employees_from_widget(employees_result)
    if people or not urn or client.calls_made >= remaining_budget:
        return people

    search_people_result = await client.search_people(keywords="Product Manager", current_company=urn)
    return parse_people_from_search(search_people_result)


async def run_contact_discovery():
    remaining_budget = preflight()
    config = load_config()
    max_contacts = config["max_contacts_per_company"]
    priority_order = config["contact_priority_order"]
    max_companies = config["max_companies_per_cycle"]

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    jobs = conn.execute(
        "SELECT * FROM jobs WHERE status = 'tailored' ORDER BY relevance_score DESC"
    ).fetchall()

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

                people = await find_company_contacts(client, job, remaining_budget)
                ranked = rank_contacts(people, priority_order, max_contacts)

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
