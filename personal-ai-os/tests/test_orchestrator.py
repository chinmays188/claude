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
    call order: (0) MultiAgentPlanner's call, but ONLY when
    might_need_multiple_agents(text) is True for the given input (a free,
    no-LLM-call heuristic gate -- short/simple test inputs below don't
    trigger it, so no response needs to be scripted for it); (1)
    DomainRouter's classification call, (2) TaskClassifier's classification
    call, (3+) the dispatched agent's own call(s)."""

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


def test_multi_agent_heuristic_not_triggered_skips_planner_call_entirely():
    """A short, simple request should never even make the MultiAgentPlanner
    call -- confirmed by NOT scripting a response for it; if the heuristic
    incorrectly fired, this test would fail with an empty-list pop error."""
    llm = ScriptedProvider(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "RAG combines retrieval with generation."}',
        ]
    )
    orchestrator = Orchestrator(llm)

    result = orchestrator.handle("Explain RAG.")

    assert result.agent == "research_agent"


def test_long_multi_clause_request_triggers_sequential_multi_agent_path():
    llm = ScriptedProvider(
        [
            '{"agents": ["research", "analysis", "planning"], "mode": "SEQUENTIAL", '
            '"reasoning": "planning needs the analysis which needs the research"}',
            '{"action": "final_answer", "answer": "Kubernetes orchestrates containers."}',
            '{"action": "final_answer", "answer": "K8s is more flexible than ECS but has a steeper learning curve."}',
            '{"action": "final_answer", "answer": "Week 1: pilot. Week 2: migrate one service."}',
        ]
    )
    orchestrator = Orchestrator(llm)
    long_request = (
        "Please research what Kubernetes actually is and how it works, then "
        "compare it against ECS for a mid-size team's real tradeoffs, and "
        "finally give me a concrete plan to adopt whichever one wins."
    )

    result = orchestrator.handle(long_request)

    assert result.agent.startswith("multi_agent:sequential:")
    assert result.output == "Week 1: pilot. Week 2: migrate one service."


def test_multi_agent_planner_failure_degrades_to_single_agent_path():
    """A malformed MultiAgentPlanner response (StructuredOutputError after
    exhausting repairs) should degrade to the normal single-agent path, not
    crash -- the request still goes through UnifiedRouter + a real agent."""
    long_request = (
        "Please research what Kubernetes actually is and how it works, then "
        "compare it against ECS for a mid-size team's real tradeoffs, and "
        "finally give me a concrete plan to adopt whichever one wins."
    )
    llm = ScriptedProvider(
        [
            "not valid json", "still not valid json", "nope",  # exhausts MultiAgentPlanner's repair attempts
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "a real answer"}',
        ]
    )
    orchestrator = Orchestrator(llm)

    result = orchestrator.handle(long_request)

    assert result.agent == "research_agent"
    assert result.output == "a real answer"


def test_on_multi_agent_planned_observer_receives_the_real_plan():
    observed = []
    llm = ScriptedProvider(
        [
            '{"agents": ["research", "analysis"], "mode": "PARALLEL", "reasoning": "independent asks"}',
            '{"action": "final_answer", "answer": "research output"}',
            '{"action": "final_answer", "answer": "analysis output"}',
            "combined synthesis output",
        ]
    )
    orchestrator = Orchestrator(llm, on_multi_agent_planned=lambda p: observed.append(p))
    long_request = (
        "Give me a thorough research summary of retrieval augmented generation "
        "and, completely separately, a risk analysis of adopting it in production."
    )

    orchestrator.handle(long_request)

    assert len(observed) == 1
    assert observed[0].mode.value == "PARALLEL"


class NamedScriptedProvider(ScriptedProvider):
    """Same scripting behavior as ScriptedProvider, but records its own
    model_name so a test can prove WHICH provider actually served a call --
    needed to verify agent_llm (the real model-routing hook) is genuinely
    used for agent generation while classification stays on the main llm."""

    def __init__(self, name: str, responses: list[str]):
        super().__init__(responses)
        self._name = name

    @property
    def model_name(self) -> str:
        return self._name


def test_agent_llm_is_used_for_agent_generation_not_classification():
    """Real model-routing integration point: classification/planning calls
    always use the main llm; the 3 agents' own generation calls use
    agent_llm when given. Defaults to llm when not given (every existing
    caller's behavior, verified by every other test in this file passing
    unchanged)."""
    classification_llm = NamedScriptedProvider(
        "classification-model",
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
        ],
    )
    agent_llm = NamedScriptedProvider(
        "agent-model",
        ['{"action": "final_answer", "answer": "answered by the routed agent model"}'],
    )
    orchestrator = Orchestrator(classification_llm, agent_llm=agent_llm)

    result = orchestrator.handle("Explain RAG.")

    assert result.output == "answered by the routed agent model"
    # Classification consumed exactly its 2 scripted responses; if the
    # agent had used classification_llm instead, this list would be empty
    # and the agent's own call would have raised IndexError.
    assert classification_llm._responses == []
