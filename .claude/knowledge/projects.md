# Projects

## job-agent (Active)
- Location: `job-agent/`
- Purpose: automated job-hunting pipeline for AI/Voice-AI/Conversational-AI PM roles (Bangalore, Delhi, Gurgaon, Noida), targeting 5+ yrs seniority
- 5-stage orchestrator (`src/orchestrator.py`): discovery → scoring (Claude relevance filter) → resume tailoring (per-job `.docx`) → contact discovery (LinkedIn) → outreach drafting + email digest
- Discovery/contacts run against the unofficial `mcp-server-linkedin` MCP server (browser automation via Playwright/Patchright) — see `errors.md` for the response-shape gotchas and the `--login` auth flow required on macOS
- Config: `config/target_profile.json` (roles/locations/seniority), `config/agent_config.json` (daily MCP call ceiling, backoff, contact limits), `config/.env` (ANTHROPIC_API_KEY, GMAIL_ADDRESS, GMAIL_APP_PASSWORD — never commit this file)
- State: SQLite at `data/job_agent.db` (`jobs`, `contacts`, `run_log` tables) + `data/runtime_state.json` (backoff state)
- `daily_mcp_call_ceiling` was raised 30 → 150 during 2026-08-08 debugging/testing; consider dialing back down for steady-state runs
- As of 2026-08-08: full pipeline verified working end-to-end — 86 jobs discovered, 7 passed scoring threshold, 7 resumes tailored, contacts found for 1 of 3 companies attempted (Coinbase/Responsive returned 0 — not yet investigated), 7 digest emails sent successfully
- Nothing is ever auto-sent to LinkedIn contacts — `outreach.py` only drafts messages; `send_message`/`connect_with_person` client methods exist (fixed for correctness) but are not called by any pipeline stage

### Resume tailoring — what changes vs. master_resume.json/pdf, and why (2026-08-08, UNVERIFIED against real Claude output — see note at bottom)

`src/tailoring.py` takes `resume/master_resume.json` (the source of truth for content) and `resume/master_resume.pdf` (the source of truth for visual design) and produces a per-job PDF in `resume/tailored/`. Two separate things get "tailored":

**1. Content selection (via Claude, changes per job)**
- `career_summary`: up to 3 bullets selected/reordered from the master list, by relevance to the specific job description
- `experience`: all roles kept, but bullets within each role reordered by relevance (bullets are never dropped, only reordered) — role/company/dates are never altered
- `skills`: split into `functional` / `interpersonal` / `technical` (matching master resume's 3 labeled categories), each filtered+ordered by relevance to the job — was previously a single flattened top-10 list with no category labels, which didn't match the master resume's structure. Fixed 2026-08-08.
- `passion_projects`: reordered by relevance. Was missing entirely from tailored output until 2026-08-08 (prompt never asked for it) — now included since the master resume has this as a real section.
- **Inline bold spans**: Claude wraps 1-3 key phrases per bullet (metrics like `₹88Cr`, `42%`, or job-relevant skill terms) in `**bold**`, converted to real PDF bold. Required because the master resume visually bolds specific phrases within bullets (not whole bullets) — matching that meant the model needs to mark emphasis, since the source JSON bullets are plain text with no markup.
- **Never invented**: the prompt explicitly forbids inventing new facts/metrics/experience — tailoring can only reorder/select/rephrase-for-keyword-alignment from what's in `master_resume.json`, never add anything not present there.

**2. Visual design (fixed, does not change per job — built to match `master_resume.pdf` exactly)**
- Output format changed from `.docx` to `.pdf` (2026-08-08, user request) — built directly with `reportlab`, no LibreOffice/system dependency
- Font: macOS's `Helvetica.ttc` registered with separate regular/bold faces (subfontIndex 0/1) + `registerFontFamily()`, required because (a) Base14 Helvetica lacks the ₹ glyph the resume content uses, and Arial Unicode.ttf — despite its name — predates the 2010 Unicode ₹ addition and also lacks it; (b) registering one face under both "regular" and "bold" names, an earlier version of this fix, silently rendered `<b>` tags as unstyled text
- Section headers ("Career Summary", "Professional Experience", etc.): full-width gray band, bold white text — was plain bordered-box headings before this matched to the master resume's actual banded-header look
- Role header rows: shaded light-gray row, bold title+company left-aligned, bold date range right-aligned — was plain unshaded left-aligned text before
- Footer: horizontal rule + centered contact line, matching master resume

**How to verify later**: open a real tailored PDF from `resume/tailored/` next to `resume/master_resume.pdf` side by side. Check: (a) does bold actually render (not just appear in `**markers**` as literal text — that was a real bug once already), (b) do the 4 sections (Career Summary, Professional Experience, Education, Skills, Passion Projects) all appear in that order, (c) does Skills show 3 labeled categories not one flat line, (d) does nothing look invented/wrong vs. the master JSON content.

**Not yet done**: this has only been tested with hand-mocked data (not a real Claude tailoring call) as of 2026-08-08 — the actual model's bold-span placement and category-filtering behavior on a real job description is unverified.

## AI Travel Agent (Prototype)
- Source: `awesome-llm-apps/starter_ai_agents/ai_travel_agent/`
- Original file: `local_travel_agent.py` — Streamlit UI, Ollama/Llama3.2, SerpAPI
- Modified: Swapped LLM to Claude (claude-sonnet-4-6)
- Prototype created: `travel_agent_prototype.py` — terminal-only, no Streamlit, no SerpAPI
- Dependencies: `agno`, `anthropic`, `icalendar`
- Requires: `ANTHROPIC_API_KEY` env variable
- Run: `python3 travel_agent_prototype.py`
- Output: prints itinerary + saves `.ics` calendar file

## Chinmay's Core Work Projects (from CLAUDE.md)
- Voice bot
- Chatbot
- Agent assist
- Email bot
- Domain: Post-sales customer experience at MakeMyTrip
