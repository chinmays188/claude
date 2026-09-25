"""Shared tool-set construction for the 3 generic agents
(ResearchAgent/AnalystAgent/PlannerAgent). Factored out so all 3 get the
same real tool access, rather than only ResearchAgent -- a real asymmetry
the user pointed out: "Why would only research agent do tool calling? Even
analyst and planner can do tool calling?" Every tool here is optional
(added only when its dependency is actually supplied), and per-request
tool use is never forced: ToolAgent's decision loop always lets the LLM
choose 'final_answer' directly when no tool is needed (see
app/agents/tool_agent.py's DECISION_PROMPT) -- adding tools to an agent
only expands what it CAN do, never what it must do every turn."""

from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.base import LLMProvider
from app.retrieval.vector_search import VectorStore
from app.tools.base import Tool
from app.tools.calculator import CalculatorTool
from app.tools.domain_workflow_tools import AnalyzeFeedbackTool, AnalyzeJdTool, DraftPrdTool
from app.tools.retrieval_tool import RetrievalTool


def build_shared_tools(
    llm: LLMProvider,
    retrieval_store: VectorStore | None = None,
    secure_retriever: SecureRetriever | None = None,
    requester_id: str | None = None,
    requester_tenant_id: str | None = None,
) -> list[Tool]:
    """calculator and analyze_feedback are always available (neither needs
    retrieval -- checked by reading app/domains/pm/feedback_intelligence.py
    directly, not assumed). retrieve, analyze_jd, and draft_prd each need
    real infra: retrieve needs a VectorStore, analyze_jd/draft_prd each need
    a SecureRetriever (they ground their output in the user's own retrieved
    documents) plus a requester identity for permission-scoped search --
    each is added independently, only when its own real dependency is
    supplied, not lumped under one shared toggle."""
    tools: list[Tool] = [CalculatorTool(), AnalyzeFeedbackTool(llm)]

    if retrieval_store is not None:
        tools.append(RetrievalTool(retrieval_store))

    if secure_retriever is not None and requester_id is not None and requester_tenant_id is not None:
        tools.append(AnalyzeJdTool(llm, secure_retriever, requester_id, requester_tenant_id))
        tools.append(DraftPrdTool(llm, secure_retriever, requester_id, requester_tenant_id))

    return tools
