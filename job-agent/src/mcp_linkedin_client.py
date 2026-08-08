import json
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def parse_tool_result(result):
    """
    CallToolResult.content is a list of content blocks (usually TextContent
    with .text holding a JSON string). Normalize to a Python object so
    callers can treat every tool response as plain dict/list data.
    """
    if result.is_error:
        raise RuntimeError(f"MCP tool call failed: {result.content}")

    texts = [block.text for block in result.content if hasattr(block, "text")]
    if not texts:
        return None
    combined = "\n".join(texts)
    try:
        return json.loads(combined)
    except json.JSONDecodeError:
        return combined

SERVER_PARAMS = StdioServerParameters(
    command="uvx",
    args=["mcp-server-linkedin@latest"],
    env={},
)


class LinkedInMCPClient:
    """
    Thin wrapper around the mcp-server-linkedin stdio server.
    Every call_tool() invocation counts as one MCP call against the daily
    ceiling — callers must check budget via state.preflight() before use
    and track call counts via self.calls_made.
    """

    def __init__(self):
        self.calls_made = 0
        self._session = None
        self._stdio_ctx = None

    async def __aenter__(self):
        self._stdio_ctx = stdio_client(SERVER_PARAMS)
        read, write = await self._stdio_ctx.__aenter__()
        self._session = ClientSession(read, write)
        await self._session.__aenter__()
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._session.__aexit__(exc_type, exc, tb)
        await self._stdio_ctx.__aexit__(exc_type, exc, tb)

    async def call(self, tool_name: str, arguments: dict):
        result = await self._session.call_tool(tool_name, arguments)
        self.calls_made += 1
        return parse_tool_result(result)

    async def search_jobs(self, keywords: str, location: str):
        return await self.call("search_jobs", {"keywords": keywords, "location": location})

    async def get_job_details(self, job_id: str):
        return await self.call("get_job_details", {"job_id": job_id})

    async def search_companies(self, keywords: str):
        return await self.call("search_companies", {"keywords": keywords})

    async def get_company_employees(self, company_name: str, keywords: str | None = None):
        args = {"company_name": company_name}
        if keywords:
            args["keywords"] = keywords
        return await self.call("get_company_employees", args)

    async def get_person_profile(self, linkedin_username: str, sections: str | None = None):
        args = {"linkedin_username": linkedin_username}
        if sections:
            args["sections"] = sections
        return await self.call("get_person_profile", args)

    async def send_message(self, linkedin_username: str, message: str, confirm_send: bool = False):
        # Only ever called after explicit user approval — see digest.py / approve flow.
        return await self.call("send_message", {
            "linkedin_username": linkedin_username, "message": message, "confirm_send": confirm_send,
        })

    async def connect_with_person(self, linkedin_username: str, note: str = ""):
        # Only ever called after explicit user approval — see digest.py / approve flow.
        return await self.call("connect_with_person", {"linkedin_username": linkedin_username, "note": note})
