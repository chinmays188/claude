from datetime import datetime, timezone

import pytest

from app.agents.base import AgentResponse
from app.agents.orchestrator import ClarificationNeeded, Orchestrator
from app.providers.base import LLMProvider
from app.retrieval.document import Chunk
from app.retrieval.vector_search import VectorStore
from tests.fakes.fake_embedding import FakeEmbeddingModel


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


def test_retrieval_store_none_by_default_matches_prior_behavior():
    """Regression guard: retrieval_store defaults to None, so ResearchAgent
    gets no retrieve tool -- identical to Orchestrator's behavior before
    this parameter existed."""
    llm = ScriptedProvider(
        [
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "no retrieval needed"}',
        ]
    )
    orchestrator = Orchestrator(llm)

    result = orchestrator.handle("Explain something.")

    assert result.tool_calls == []  # no retrieve tool was ever available to call


def test_retrieval_store_passed_through_to_research_agent():
    now = datetime.now(timezone.utc)
    store = VectorStore(FakeEmbeddingModel())
    store.add([Chunk(id="doc1::c0", document_id="doc1", text="Kubernetes is a container orchestrator.",
                      source="notes", created_at=now, updated_at=now, chunk_index=0)])

    llm = ScriptedProvider(
        [
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "call_tool", "tool": "retrieve", "args": {"query": "Kubernetes"}}',
            '{"action": "final_answer", "answer": "Kubernetes orchestrates containers."}',
        ]
    )
    orchestrator = Orchestrator(llm, retrieval_store=store)

    result = orchestrator.handle("What is Kubernetes?")

    assert "retrieve" in result.tool_calls


def test_on_tool_call_forwarded_to_research_agent():
    observed = []
    now = datetime.now(timezone.utc)
    store = VectorStore(FakeEmbeddingModel())
    store.add([Chunk(id="doc1::c0", document_id="doc1", text="Kubernetes is a container orchestrator.",
                      source="notes", created_at=now, updated_at=now, chunk_index=0)])

    llm = ScriptedProvider(
        [
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "call_tool", "tool": "retrieve", "args": {"query": "Kubernetes"}}',
            '{"action": "final_answer", "answer": "done"}',
        ]
    )
    orchestrator = Orchestrator(
        llm, retrieval_store=store,
        on_tool_call=lambda name, args, result: observed.append((name, args, result)),
    )

    orchestrator.handle("What is Kubernetes?")

    assert len(observed) == 1
    assert observed[0][0] == "retrieve"
