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
