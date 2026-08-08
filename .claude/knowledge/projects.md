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
