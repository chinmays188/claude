from datetime import datetime, timezone

import pytest

from app.agents.base import AgentResponse
from app.agents.orchestrator import ClarificationNeeded, Orchestrator
from app.providers.base import LLMProvider
from app.retrieval.document import Chunk
from app.retrieval.vector_search import VectorStore
from tests.fakes.fake_embedding import FakeEmbeddingModel


class ScriptedProvider(LLMProvider):
    """Returns responses in sequence, matching Orchestrator.handle()'s real
    call order via UnifiedRouter: (1) DomainRouter's classification call,
    (2) TaskClassifier's classification call, (3+) the dispatched agent's
    own call(s)."""

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
            '{"domains": [], "confidence": 0.9}',
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
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "analysis", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "RAG is better for freshness; fine-tuning for style."}',
        ]
    )
    orchestrator = Orchestrator(llm)

    result = orchestrator.handle("Compare RAG and fine-tuning.")

    assert result.agent == "analyst_agent"


def test_planning_request_routes_to_planner_agent():
    llm = ScriptedProvider(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "planning", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "Week 1: Docker basics..."}',
        ]
    )
    orchestrator = Orchestrator(llm)

    result = orchestrator.handle("Create a 30-day plan for learning Docker.")

    assert result.agent == "planner_agent"


def test_ambiguous_request_returns_clarification_without_calling_agent():
    llm = ScriptedProvider(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "unclear", "confidence": 0.9}',
        ]
    )
    orchestrator = Orchestrator(llm)

    result = orchestrator.handle("Do something useful.")

    assert isinstance(result, ClarificationNeeded)
    assert result.input == "Do something useful."


def test_low_confidence_returns_clarification():
    llm = ScriptedProvider(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.1}',
        ]
    )
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
            '{"domains": [], "confidence": 0.9}',
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
            '{"domains": [], "confidence": 0.9}',
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
            '{"domains": [], "confidence": 0.9}',
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


def test_domain_is_injected_as_context_into_the_agent_prompt():
    """The combined router's whole point: a classified domain should reach
    the dispatched agent, not be discarded after routing."""
    seen_prompts = []

    class RecordingProvider(LLMProvider):
        def __init__(self, responses):
            self._responses = list(responses)

        def generate(self, prompt: str) -> str:
            seen_prompts.append(prompt)
            return self._responses.pop(0)

        @property
        def model_name(self) -> str:
            return "scripted-model"

    llm = RecordingProvider(
        [
            '{"domains": ["CAREER"], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "answer"}',
        ]
    )
    orchestrator = Orchestrator(llm)

    orchestrator.handle("Should I learn Kubernetes for my career?")

    # The third call is ResearchAgent's decision prompt -- it should
    # contain the classified domain, not just the raw user text.
    assert "CAREER" in seen_prompts[2]


def test_general_domain_adds_no_context_noise():
    """When DomainRouter finds no domain (GENERAL), the agent's prompt
    should be unmodified -- no injected label for a request that doesn't
    belong to any Phase 3 domain."""
    seen_prompts = []

    class RecordingProvider(LLMProvider):
        def __init__(self, responses):
            self._responses = list(responses)

        def generate(self, prompt: str) -> str:
            seen_prompts.append(prompt)
            return self._responses.pop(0)

        @property
        def model_name(self) -> str:
            return "scripted-model"

    llm = RecordingProvider(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "42*12 is 504"}',
        ]
    )
    orchestrator = Orchestrator(llm)

    orchestrator.handle("What is 42 times 12?")

    assert "domain" not in seen_prompts[2].lower()


def test_domain_classification_failure_returns_clarification_not_crash():
    """UnifiedRoutingError (e.g. malformed structured output that exhausts
    repair attempts) should degrade to a clarification, not propagate as an
    unhandled exception to the caller (app/main.py, voice_api.py)."""
    llm = ScriptedProvider(["not valid json at all", "still not valid json", "nope"])
    orchestrator = Orchestrator(llm)

    result = orchestrator.handle("Some request.")

    assert isinstance(result, ClarificationNeeded)


def test_on_classified_observer_receives_the_real_classification():
    observed = []
    llm = ScriptedProvider(
        [
            '{"domains": ["FINANCE"], "confidence": 0.9}',
            '{"task_type": "analysis", "confidence": 0.85}',
            '{"action": "final_answer", "answer": "some analysis"}',
        ]
    )
    orchestrator = Orchestrator(llm, on_classified=lambda c: observed.append(c))

    orchestrator.handle("Compare my portfolio options.")

    assert len(observed) == 1
    assert observed[0].domain.value == "FINANCE"
    assert observed[0].task_type.value == "analysis"


def test_on_classified_still_fires_for_unclear_task_type():
    """The observer should see the classification even when task_type is
    UNCLEAR and handle() returns ClarificationNeeded -- the classification
    itself is real and happened, regardless of what handle() does with it."""
    observed = []
    llm = ScriptedProvider(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "unclear", "confidence": 0.2}',
        ]
    )
    orchestrator = Orchestrator(llm, on_classified=lambda c: observed.append(c))

    orchestrator.handle("hmm")

    assert len(observed) == 1
    assert observed[0].task_type.value == "unclear"
