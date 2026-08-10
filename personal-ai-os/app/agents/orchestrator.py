from pydantic import BaseModel

from app.agents.analyst_agent import AnalystAgent
from app.agents.base import AgentResponse
from app.agents.planner_agent import PlannerAgent
from app.agents.research_agent import ResearchAgent
from app.providers.base import LLMProvider
from app.routing.classifier import TaskClassifier, TaskType


class ClarificationNeeded(BaseModel):
    input: str
    message: str


class Orchestrator:
    def __init__(self, llm: LLMProvider):
        self._classifier = TaskClassifier(llm)
        self._agents = {
            TaskType.RESEARCH: ResearchAgent(llm),
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
