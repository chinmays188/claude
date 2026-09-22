from pydantic import BaseModel

from app.agents.analyst_agent import AnalystAgent
from app.agents.base import AgentResponse
from app.agents.planner_agent import PlannerAgent
from app.agents.research_agent import ResearchAgent
from app.providers.base import LLMProvider
from app.retrieval.vector_search import VectorStore
from app.routing.classifier import TaskClassifier, TaskType


class ClarificationNeeded(BaseModel):
    input: str
    message: str


class Orchestrator:
    def __init__(self, llm: LLMProvider, retrieval_store: VectorStore | None = None, on_tool_call=None):
        # retrieval_store is optional and additive: passing None (the
        # default, matching every existing caller's behavior exactly)
        # constructs ResearchAgent without a retrieve tool, same as before.
        # Passing a real VectorStore lets ResearchAgent's retrieve tool
        # actually ground answers in indexed documents. on_tool_call is
        # forwarded to ResearchAgent (the only agent here with a tool loop)
        # for callers that need real tool-call I/O visibility.
        self._classifier = TaskClassifier(llm)
        self._agents = {
            TaskType.RESEARCH: ResearchAgent(llm, store=retrieval_store, on_tool_call=on_tool_call),
            TaskType.ANALYSIS: AnalystAgent(llm),
            TaskType.PLANNING: PlannerAgent(llm),
        }

    def handle(self, text: str) -> AgentResponse | ClarificationNeeded:
        if not text or not text.strip():
            raise ValueError("Input text must not be empty.")

        classification = self._classifier.classify(text)

        if classification.task_type == TaskType.UNCLEAR:
            return ClarificationNeeded(
                input=text,
                message=(
                    "I'm not sure what you'd like me to do. Could you clarify "
                    "whether this is a research, analysis, or planning request?"
                ),
            )

        agent = self._agents[classification.task_type]
        return agent.run(text)
