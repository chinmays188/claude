from app.agents.agent_tools import build_shared_tools
from app.agents.tool_agent import ToolAgent
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.base import LLMProvider
from app.retrieval.vector_search import VectorStore
from app.tools.base import Tool
from app.tools.registry import ToolRegistry


class ResearchAgent(ToolAgent):
    name = "research_agent"
    system_prompt = (
        "You are a research agent. Explain the topic clearly, include a "
        "concrete example, and note any important limitations or caveats. "
        "Use the calculator tool for numeric computation. Use the retrieve tool "
        "to ground answers in the local knowledge base when it might have "
        "relevant information; cite sources by their chunk id when you do. "
        "Use analyze_feedback/analyze_jd/draft_prd when the request matches "
        "what they're for. Use any mcp_* tool when the request matches a "
        "connected external service (e.g. GitHub)."
    )

    def __init__(
        self, llm: LLMProvider, store: VectorStore | None = None, on_tool_call=None, on_tool_error=None,
        secure_retriever: SecureRetriever | None = None, requester_id: str | None = None,
        requester_tenant_id: str | None = None, mcp_tools: list[Tool] | None = None,
        policy_engine=None,
    ):
        tools = build_shared_tools(llm, store, secure_retriever, requester_id, requester_tenant_id, mcp_tools)
        super().__init__(llm, tools=ToolRegistry(tools), on_tool_call=on_tool_call, on_tool_error=on_tool_error, policy_engine=policy_engine)
