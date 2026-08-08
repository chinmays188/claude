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
