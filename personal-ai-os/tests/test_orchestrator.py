import pytest

from app.agents.base import AgentResponse
from app.agents.orchestrator import ClarificationNeeded, Orchestrator
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    """Returns responses in sequence: first call is the classifier, second is the agent."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_research_request_routes_to_research_agent():
    llm = ScriptedProvider(
        [
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "RAG combines retrieval with generation."}',
        ]
    )
    orchestrator = Orchestrator(llm)

    result = orchestrator.handle("Explain RAG.")

    assert isinstance(result, AgentResponse)
    assert result.agent == "research_agent"


def test_analysis_request_routes_to_analyst_agent():
    llm = ScriptedProvider(
        [
            '{"task_type": "analysis", "confidence": 0.9}',
            "RAG is better for freshness; fine-tuning for style.",
        ]
    )
    orchestrator = Orchestrator(llm)

    result = orchestrator.handle("Compare RAG and fine-tuning.")

    assert result.agent == "analyst_agent"


def test_planning_request_routes_to_planner_agent():
    llm = ScriptedProvider(
        [
            '{"task_type": "planning", "confidence": 0.9}',
            "Week 1: Docker basics...",
        ]
    )
    orchestrator = Orchestrator(llm)

    result = orchestrator.handle("Create a 30-day plan for learning Docker.")

    assert result.agent == "planner_agent"


def test_ambiguous_request_returns_clarification_without_calling_agent():
    llm = ScriptedProvider(['{"task_type": "unclear", "confidence": 0.9}'])
    orchestrator = Orchestrator(llm)

    result = orchestrator.handle("Do something useful.")

    assert isinstance(result, ClarificationNeeded)
    assert result.input == "Do something useful."


def test_low_confidence_returns_clarification():
    llm = ScriptedProvider(['{"task_type": "research", "confidence": 0.1}'])
    orchestrator = Orchestrator(llm)

    result = orchestrator.handle("hmm")

    assert isinstance(result, ClarificationNeeded)


def test_empty_input_raises_before_classification():
    llm = ScriptedProvider([])
    orchestrator = Orchestrator(llm)

    with pytest.raises(ValueError):
        orchestrator.handle("")
