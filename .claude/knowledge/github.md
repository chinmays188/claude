# GitHub

## Forked Repos
| Repo | Original | Local Path |
|------|----------|------------|
| chinmays188/awesome-llm-apps | Shubhamsaboo/awesome-llm-apps | `/Users/chinmay/claude.md/Project/awesome-llm-apps` |
| chinmays188/agency-agents | msitarzewski/agency-agents | `/Users/chinmay/claude.md/Project/agency-agents` |

## SSH Setup
- Key type: ed25519
- Email: chinmays188@gmail.com
- Both remotes updated to SSH (`git@github.com:chinmays188/...`)

## Changes Pushed
- `awesome-llm-apps`: Swapped Ollama/Llama3.2 → Claude (claude-sonnet-4-6) in `local_travel_agent.py`
- `claude` repo, commit `290b3f9` (2026-08-08): Added `job-agent/` (LinkedIn job discovery → Claude scoring → resume tailoring → contact discovery → outreach drafting → email digest pipeline); fixed MCP/Anthropic SDK response-shape bugs (see `errors.md`); consolidated `.claude/.mcp.json` → root `.mcp.json`. First push was blocked by GitHub secret scanning (`job-agent/config/.env.example` had a real Anthropic key + Gmail app password committed instead of blank placeholders) — amended the commit to strip secrets before the successful push. Both exposed credentials should be rotated.
- `claude` repo, commit `077cb56` (2026-08-08): Reworked job-agent's scoring (batched calls, top-10 ranking, location/company exclusion filters), tailoring (.docx → PDF matching master_resume.pdf's design), contacts (company verification, search_people fallback, fixed a classify_contact bug and a job-ordering bug), outreach (grounded in real JD/resume content, 300-word cap), and orchestrator (per-stage state tracking + resume support) — all verified against real live data today. Also fixed a bug where discovery.py discarded the real scraped job location in favor of a placeholder, and reset `daily_mcp_call_ceiling` to a real steady-state value (200) after today's testing bumps.
- `claude` repo, commit `248d07a` (2026-08-08): Addressed user's 6-point feedback list on job-agent — digest email now includes job_url and relevance_reason plus an explanation when contacts are missing; scoring.py switched from pure top-N to threshold(>=0.6)+cap(10) selection and flipped its location filter from blocklist to allowlist (requires a positive India/target-city match) with a second LLM-driven JD-content location check to catch mistagged postings (e.g. a "New Delhi"-tagged US-remote role); tailoring.py now progressively shrinks font/spacing/content until the resume strictly fits one page; contacts.py writes contact_search_status (found/no_contacts_found/company_unverified) with a reason. Verified live against real jobs (Instacart + 6 mistagged US roles correctly rejected; BiteSpeed contact discovery end-to-end). `daily_mcp_call_ceiling` was temporarily bumped to 350 for testing and reset back to 200 afterward.
