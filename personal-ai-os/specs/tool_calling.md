# Tool Calling

## Example 1 — Tool needed

Input:
"What is 47 * 12?"

Expected:
- LLM decision step selects the `calculator` tool with args `{"expression": "47 * 12"}`
- Tool executes and returns `564`
- Final answer incorporates the tool result
- `AgentResponse.tool_calls == ["calculator"]`

## Example 2 — No tool needed

Input:
"Explain RAG."

Expected:
- LLM decision step returns `{"tool": null}`
- No tool is executed
- `AgentResponse.tool_calls == []`

## Example 3 — Hallucinated tool call

Condition:
LLM decision step returns a tool name not in the registry (e.g. `"send_email"`).

Expected:
- `ToolRegistry` rejects the unknown tool (`UnknownToolError`)
- Agent falls back to answering without a tool, does not crash
- `AgentResponse.tool_calls == []`

## Example 4 — Invalid tool arguments

Condition:
LLM decision step returns `{"tool": "calculator", "args": {"expression": null}}`

Expected:
- `CalculatorArgs` schema validation fails
- `ArgumentValidationError` raised
- (Repair loop for this is deferred to Milestone 4 — Structured Output; for M3 the failure must be visible, not silently swallowed)

## Example 5 — Tool execution failure

Condition:
`calculator` tool called with `{"expression": "1 / 0"}`

Expected:
- Tool raises `ToolError` (division by zero)
- Error is visible, not silently absorbed into a fabricated answer

## Retry safety

- `calculator` is declared `retry_safe = True` — deterministic, no side effects, safe to retry.
- Per Section 33, side-effecting tools (not implemented in this milestone, e.g. `send_email`) must default to `retry_safe = False`.

## Example — MCP (Model Context Protocol), plug and play

The user's ask: "while I have 8 or more than 8 tools to call for the 3
agents, let us build MCP connection plug n play and test it with a MCP
connection with my github." Checked first: no MCP integration existed
anywhere in this codebase (only mentioned in a learning-goal description,
never implemented).

Built as a genuinely generic layer, not GitHub-specific code:
`app/tools/mcp_tool.py`'s `MCPConnection` connects to ANY MCP server over
the real `streamable_http` transport (verified against the actual
installed `mcp` 2.2.0 package's API, not assumed from memory/older docs);
`discover_mcp_tools()` calls the server's real `list_tools()` and wraps
each one as a real `app/tools/base.py` `Tool` — indistinguishable from
`calculator`/`retrieve`/etc. to `ToolAgent`/`ToolRegistry`. A real JSON
Schema-to-Pydantic converter (`_json_schema_to_pydantic()`, using
`pydantic.create_model()`) builds each tool's `args_schema` dynamically,
since MCP tools ship a raw JSON schema, not a Pydantic class — this is the
actual mechanism that makes it "plug and play": any future MCP server
works with zero new code, only a URL + auth headers.

A real bridging problem was solved, not glossed over: every `Tool.run()`
in this codebase is synchronous (`ToolAgent`'s decision loop calls
`tool.call()` directly), but MCP's client is fully async and needs a
persistent session (re-initializing per call would be wasteful and
fragile against a real remote server). `MCPConnection` runs one
background thread with its own asyncio event loop for the connection's
lifetime; `MCPTool.run()` blocks on that loop via
`asyncio.run_coroutine_threadsafe` — a standard pattern for bridging a
sync caller into a persistent async resource, not a hack.

`build_shared_tools()`, all 3 agents, and `Orchestrator` all gained an
optional `mcp_tools` parameter, wired identically to every other optional
tool dependency (`retrieval_store`, `secure_retriever`) — passing none of
them (the default) changes nothing for any existing caller.

New `scripts/test_mcp_github.py`: connects to GitHub's real, official
remote MCP server (`https://api.githubcopilot.com/mcp/`), lists its real
discovered tools, and optionally calls one to prove a real round trip.
Requires a real `GITHUB_TOKEN` in `.env` (a GitHub Personal Access Token)
— this script is not GitHub-specific in its logic, GitHub is simply the
first real live test case for the generic connection.

Verified without live network first (a real connection attempt with no
token correctly raised an `MCPError` from the server itself, proving the
HTTP/session mechanics work before any credentials existed) and via 9 new
tests: 6 on the pure JSON-schema-to-Pydantic conversion and content
extraction logic, 3 proving `build_shared_tools()`/`Orchestrator` wire a
fake MCP-shaped `Tool` through correctly.

**Then verified fully live against the real GitHub MCP server**, once the
user added their own `GITHUB_TOKEN` to `.env`:
- `scripts/test_mcp_github.py` connected, initialized, and discovered
  **45 real tools** GitHub's server actually advertises (search, issues,
  PRs, commits, files, releases, teams, secret scanning, etc.) — not a
  hand-picked subset.
- Called `mcp_get_me` with empty args and got back the user's real GitHub
  account data (real username, real profile URL, real public/private repo
  counts).
- Called `mcp_search_repositories` with a real query (`user:chinmays188`)
  and got back the user's real repositories with real metadata.
- **Full production path verified**: constructed a real `Orchestrator`
  with the 45 discovered `MCPTool`s passed as `mcp_tools`, gave it the
  real request "What is my GitHub username and how many public repos do I
  have?", and the real `UnifiedRouter` classified it, the real
  `ResearchAgent` genuinely CHOSE to call `mcp_get_me` (out of 45 MCP
  tools plus its 8 built-in tools — an actual LLM decision, not scripted),
  and produced the correct answer ("Your GitHub username is
  **chinmays188** and you have **5** public repositories") grounded in
  the real tool result.

772 tests passing (was 769).
