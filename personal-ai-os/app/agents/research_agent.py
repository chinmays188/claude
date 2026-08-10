from app.agents.tool_agent import ToolAgent
from app.providers.base import LLMProvider
from app.retrieval.vector_search import VectorStore
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry
from app.tools.retrieval_tool import RetrievalTool


class ResearchAgent(ToolAgent):
    name = "research_agent"
    system_prompt = (
        "You are a research agent. Explain the topic clearly, include a "
        "concrete example, and note any important limitations or caveats. "
        "Use the calculator tool for numeric computation. Use the retrieve tool "
        "to ground answers in the local knowledge base when it might have "
        "relevant information; cite sources by their chunk id when you do."
    )

    def __init__(self, llm: LLMProvider, store: VectorStore | None = None):
        tools = [CalculatorTool()]
        if store is not None:
            tools.append(RetrievalTool(store))
        super().__init__(llm, tools=ToolRegistry(tools))
