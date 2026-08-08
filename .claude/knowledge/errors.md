# Errors

## Git push via HTTPS failed
- Error: `fatal: could not read Username for 'https://github.com': Device not configured`
- Cause: HTTPS remotes require stored credentials, not configured on this machine
- Resolution: Generated SSH key, added to GitHub, switched remotes to SSH

## pip/python not found
- Error: `zsh: command not found: pip` and `zsh: command not found: python`
- Cause: Python 3.9.6 was installed (system) but `pip` and `python` aliases not set
- Resolution: Use `pip3` and `python3` instead

## Tool failure: Bash (2026-08-05 03:03)
- Error: `Exit code 1
ls: /Users/chinmay/.claude/CLAUDE.md: No such file or directory`
- Input: `{"command":"ls -la ~/.claude/CLAUDE.md 2>&1","description":"Check if global CLAUDE.md exists"}`

## Tool failure: Bash (2026-08-08 04:12)
- Error: `Exit code 127
(eval):1: command not found: gh
---README---
(eval):1: command not found: gh`
- Input: `{"command":"gh repo view chinmays188/linkedin-mcp-server --json description,homepageUrl,url 2>&1; echo \"---README---\"; gh api repos/chinmays188/linkedin-mcp-server/readme -H \"Accept: application/vnd.github.raw\" 2>&1","description":"Fetch repo info and README via gh CLI"}`

## Tool failure: Bash (2026-08-08 04:22)
- Error: `Exit code 1
ls: /Users/chinmay/claude.md/Project/.mcp.json: No such file or directory
---
cat: /Users/chinmay/claude.md/Project/.mcp.json: No such file or directory`
- Input: `{"command":"ls -la /Users/chinmay/claude.md/Project/.mcp.json 2>&1; echo \"---\"; cat /Users/chinmay/claude.md/Project/.mcp.json 2>&1","description":"Check if project .mcp.json exists"}`

## Duplicate MCP config files (2026-08-08)
- Error: Two `.mcp.json` files existed — root `/Users/chinmay/claude.md/Project/.mcp.json` (linkedin server) and `.claude/.mcp.json` (github, atlassian servers) — split MCP server config across two locations
- Cause: New MCP servers were added to `.claude/.mcp.json` instead of the project-scoped root file
- Resolution: Merged all servers into root `.mcp.json`, deleted `.claude/.mcp.json`
- Conclusion: Root `.mcp.json` is the single canonical location for this project. All future MCP server additions go there — matches existing CLAUDE.md guidance ("New MCP servers go in project-scoped .mcp.json, not local config")

## job-agent: venv pointed to old project path (2026-08-08)
- Error: `venv/bin/pip: bad interpreter: /Users/chinmay/Desktop/job-agent/venv/bin/python3.14: no such file or directory`
- Cause: `job-agent/venv` was created before the project moved from `~/Desktop/job-agent` to `claude.md/Project/job-agent`; venv shebangs hardcode the absolute path at creation time and don't follow a move
- Resolution: `rm -rf venv && python3 -m venv venv && venv/bin/pip install -r requirements.txt`
- Conclusion: moving a Python project directory always requires recreating its venv, not just `git mv`-ing the folder

## job-agent: LinkedIn MCP server hangs with no output (2026-08-08)
- Error: `mcp-server-linkedin` (via `uvx`) hung indefinitely on `search_jobs`/`get_job_details` with zero output, no exception, no timeout — looked identical across different queries/locations
- Cause (multi-layered, each masked the next):
  1. Stale MCP server processes from an earlier session/Claude Desktop were holding a browser profile lock (`BrowserBusyError`) — killing them fixed one class of hang
  2. Chrome's cookie store uses app-bound encryption on this machine; `--import-from-browser chrome` times out trying to read the macOS Keychain and can never decrypt cookies — no popup, no error, just a silent timeout
  3. Real fix: run `uvx mcp-server-linkedin@latest --login` once interactively — opens its own dedicated browser profile for a manual LinkedIn login, persists session to `~/.linkedin-mcp/`, and avoids Chrome cookie decryption entirely
- Conclusion: for this MCP server, prefer `--login` over `--import-from-browser` on macOS. If a call hangs with zero output, check for stale `mcp-server-linkedin`/`uvx` processes first (`ps aux | grep mcp-server-linkedin`) before assuming an auth problem

## job-agent: MCP/Anthropic SDK response-shape mismatches (2026-08-08)
- Error: multiple silent failures traced back to job-agent's Python code assuming response shapes that didn't match the installed SDK versions or the MCP server's actual tool contract:
  - `result.isError` (camelCase) vs. the installed `mcp` package's real attribute `result.is_error` (snake_case) — caused every real LinkedIn tool call to throw inside async teardown, which looked like an infinite hang rather than a clean error
  - `response.content[0].text` assumed index 0 is always the text block; `claude-sonnet-5` sometimes returns a `ThinkingBlock` first — fixed by scanning for the first block with a `.text` attribute
  - `discovery.py` assumed `search_jobs()` returns `{"jobs": [{...structured...}]}`; the real server returns `{"job_ids": [...], "sections": {"search_results": "<scraped innerText>"}}` — no structured fields at all, just raw page text + a parallel ID list in DOM order
  - `contacts.py` called `get_company_employees(company=...)` and `get_person_profile(profile_url=...)`; real tool signatures are `get_company_employees(company_name, keywords=...)` (company_name must be the URL slug, not display name) and `get_person_profile(linkedin_username, ...)` (username, not URL) — and both return raw scraped text + a `references` list (typed `{kind, url, text}`), not structured objects
- Resolution: rewrote `discovery.py`/`contacts.py` parsers to consume raw text + references correctly (position-matched via DOM order); fixed all `mcp_linkedin_client.py` method signatures to match real tool params
- Conclusion: **never trust third-party MCP server response shapes from memory or by analogy to a "normal" API — always verify against the actual installed package's tool signatures/docstrings (via `pip download --no-deps` + unzip, or a debug script) before writing parsing logic.** Same applies to Anthropic SDK response objects — extended thinking changes `response.content` shape, so always scan for `.text` rather than indexing.

## job-agent: load_dotenv() silently no-ops if shell already has an empty var set (2026-08-08)
- Error: `ANTHROPIC_API_KEY not set` raised by `scoring.py` even though `config/.env` had a real key and `load_dotenv()` was called
- Cause: `python-dotenv`'s `load_dotenv()` does not override existing environment variables by default — if the shell already exported `ANTHROPIC_API_KEY=""` (even empty) from earlier testing, `.env`'s value is silently ignored
- Resolution: call `load_dotenv(path, override=True)` in every entrypoint (`orchestrator.py`, `scoring.py`, `tailoring.py`, `outreach.py`)
- Conclusion: always pass `override=True` unless there's a specific reason to let real shell env vars win over `.env`
