"""Tests that MCP-discovered tools are wired into build_shared_tools() /
the 3 agents / Orchestrator identically to every other optional tool
dependency -- using a fake Tool standing in for a real MCPTool (no live
network needed to prove the wiring itself is correct)."""

from pydantic import BaseModel

from app.agents.agent_tools import build_shared_tools
from app.agents.orchestrator import Orchestrator
from app.providers.base import LLMProvider
from app.tools.base import Tool


class FakeArgs(BaseModel):
    query: str


class FakeMCPTool(Tool):
    """Stands in for a real MCPTool without a live MCP connection."""

    name = "mcp_search_repos"
    description = "Fake MCP-discovered tool."
    args_schema = FakeArgs
    permissions = ["mcp:external"]

    def run(self, args: FakeArgs) -> str:
        return f"searched for {args.query}"


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_build_shared_tools_includes_mcp_tools_when_provided():
    tools = build_shared_tools(ScriptedProvider([]), mcp_tools=[FakeMCPTool()])
    names = [t.name for t in tools]
    assert "mcp_search_repos" in names


def test_build_shared_tools_omits_mcp_tools_when_not_provided():
    tools = build_shared_tools(ScriptedProvider([]))
    names = [t.name for t in tools]
    assert not any(n.startswith("mcp_") for n in names)


def test_orchestrator_research_agent_can_call_an_mcp_tool():
    llm = ScriptedProvider(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "call_tool", "tool": "mcp_search_repos", "args": {"query": "test"}}',
            '{"action": "final_answer", "answer": "found it"}',
        ]
    )
    orchestrator = Orchestrator(llm, mcp_tools=[FakeMCPTool()])

    result = orchestrator.handle("Search for something on GitHub.")

    assert "mcp_search_repos" in result.tool_calls
