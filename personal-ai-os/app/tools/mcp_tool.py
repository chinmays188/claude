"""Generic, plug-and-play MCP (Model Context Protocol) client integration.

The user's ask: "while I have 8 or more than 8 tools to call for the 3
agents, let us build MCP connection plug n play and test it with a MCP
connection with my github." Built as a genuinely generic layer -- an
MCPConnection to ANY remote MCP server (not GitHub-specific code), which
dynamically discovers that server's real tools and wraps each one as a
real app/tools/base.py Tool. This means ToolAgent/ToolRegistry work
completely unchanged: an MCP-discovered tool looks exactly like
CalculatorTool or any other Tool to the rest of this codebase. Any other
MCP server (not just GitHub) works the same way, with zero new code --
that's the actual "plug and play" part.

Real, verified API surface (checked directly against the installed `mcp`
2.2.0 package, not assumed from memory/older docs):
  - mcp.client.streamable_http.streamable_http_client(url, http_client=...)
    -> yields (read_stream, write_stream)
  - mcp.ClientSession(read_stream, write_stream) -- must call .initialize()
    before .list_tools()/.call_tool()
  - types.Tool has name/description/input_schema (real JSON schema dict,
    not a Pydantic model -- converted here via pydantic.create_model())
  - types.CallToolResult has .content (list of TextContent/ImageContent/...)
    and .is_error

Real bridging problem solved: every Tool.run() in this codebase is
SYNCHRONOUS (ToolAgent's decision loop calls tool.call() directly, no
async anywhere in that path), but MCP's client is fully async and needs a
persistent session (re-initializing per call would be wasteful and
fragile against a real remote server). MCPConnection runs one background
thread with its own asyncio event loop for the connection's lifetime,
and MCPTool.run() blocks on that loop via asyncio.run_coroutine_threadsafe
-- a real, standard pattern for bridging sync callers into a persistent
async resource, not a hack.
"""

import asyncio
import threading
from typing import Any

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pydantic import BaseModel, create_model

from app.tools.base import Tool, ToolError


class MCPConnectionError(ToolError):
    pass


def _json_schema_to_pydantic(name: str, schema: dict) -> type[BaseModel]:
    """Converts a real MCP tool's input_schema (a JSON Schema dict) into a
    real Pydantic model class, so it satisfies Tool.args_schema's contract
    (a Pydantic model type) without hand-writing one class per remote tool
    -- this is the actual mechanism that makes MCP tools "plug and play"
    rather than requiring a new Tool subclass per server."""
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    type_map = {"string": str, "integer": int, "number": float, "boolean": bool, "array": list, "object": dict}
    fields: dict[str, Any] = {}
    for prop_name, prop_schema in properties.items():
        py_type = type_map.get(prop_schema.get("type", "string"), str)
        if prop_name in required:
            fields[prop_name] = (py_type, ...)
        else:
            fields[prop_name] = (py_type | None, None)

    return create_model(f"{name}Args", **fields)


class MCPConnection:
    """Owns one persistent connection to one remote MCP server, in a
    dedicated background thread with its own event loop -- so every
    MCPTool.run() (synchronous, called from ToolAgent's sync decision
    loop) can block on real async MCP calls without each Tool needing to
    know anything about asyncio."""

    def __init__(self, url: str, headers: dict[str, str] | None = None, connect_timeout: float = 15.0):
        self._url = url
        self._headers = headers or {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._session: ClientSession | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._connect_error: Exception | None = None
        self._connect_timeout = connect_timeout
        self._stop_event: asyncio.Event | None = None

    def connect(self) -> "MCPConnection":
        """Starts the background thread, connects, and initializes the MCP
        session. Blocks (from the caller's synchronous perspective) until
        ready or connect_timeout elapses."""
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=self._connect_timeout):
            raise MCPConnectionError(f"Timed out connecting to MCP server at {self._url}")
        if self._connect_error is not None:
            raise MCPConnectionError(f"Failed to connect to MCP server at {self._url}: {self._connect_error}")
        return self

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._session_lifetime())

    async def _session_lifetime(self) -> None:
        self._stop_event = asyncio.Event()
        try:
            http_client = httpx2.AsyncClient(headers=self._headers)
            async with streamable_http_client(self._url, http_client=http_client) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    self._session = session
                    self._ready.set()
                    await self._stop_event.wait()
        except Exception as exc:  # noqa: BLE001 -- surfaced to the connecting thread, not swallowed
            self._connect_error = exc
            self._ready.set()

    def list_tools(self) -> list:
        """Returns the real list of mcp.types.Tool the server actually
        advertises -- discovered live, never hand-written."""
        return self._run_sync(self._session.list_tools()).tools

    def call_tool(self, name: str, arguments: dict) -> str:
        result = self._run_sync(self._session.call_tool(name, arguments))
        if result.is_error:
            raise ToolError(f"MCP tool '{name}' returned an error: {_extract_text(result.content)}")
        return _extract_text(result.content)

    def _run_sync(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30.0)

    def close(self) -> None:
        if self._loop is not None and self._stop_event is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread is not None:
            self._thread.join(timeout=5.0)


def _extract_text(content_blocks: list) -> str:
    """MCP tool results are a list of content blocks (TextContent,
    ImageContent, ...); this project's Tool.run() contract returns plain
    str, so text blocks are joined and non-text blocks are named rather
    than silently dropped."""
    parts = []
    for block in content_blocks:
        if hasattr(block, "text"):
            parts.append(block.text)
        else:
            parts.append(f"[non-text content: {type(block).__name__}]")
    return "\n".join(parts) if parts else "(empty result)"


class MCPTool(Tool):
    """Wraps ONE tool discovered from a live MCPConnection as a real
    app/tools/base.py Tool -- indistinguishable from any other Tool to
    ToolAgent/ToolRegistry. retry_safe defaults to False since an
    arbitrary remote MCP tool's side-effect safety is unknown (unlike
    this project's own read-only tools, which explicitly opt into
    retry_safe=True)."""

    def __init__(self, connection: MCPConnection, mcp_tool):
        self._connection = connection
        self._mcp_tool_name = mcp_tool.name
        self.name = f"mcp_{mcp_tool.name}"
        self.description = mcp_tool.description or f"MCP tool '{mcp_tool.name}' (no description provided)."
        self.args_schema = _json_schema_to_pydantic(mcp_tool.name, mcp_tool.input_schema or {})
        self.permissions = ["mcp:external"]
        self.retry_safe = False

    def run(self, args: BaseModel) -> str:
        return self._connection.call_tool(self._mcp_tool_name, args.model_dump(exclude_none=True))


def discover_mcp_tools(connection: MCPConnection) -> list[MCPTool]:
    """The actual 'plug and play' entry point: given a connected
    MCPConnection, returns a real Tool for every tool that server
    currently advertises -- works identically for GitHub's MCP server,
    or any other MCP server, with zero server-specific code."""
    return [MCPTool(connection, t) for t in connection.list_tools()]
