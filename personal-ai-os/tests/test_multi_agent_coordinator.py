import time

import pytest

from app.agents.base import AgentResponse
from app.agents.multi_agent_coordinator import (
    AgentName,
    CoordinationMode,
    MultiAgentCoordinator,
    MultiAgentPlan,
    MultiAgentPlanner,
    MultiAgentPlanningError,
)
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


class SlowStubAgent:
    """Sleeps for a real, measurable duration before returning -- used to
    prove _run_parallel() actually runs agents concurrently (real wall-clock
    time ~= max(delays), not sum(delays))."""

    def __init__(self, name: str, output: str, delay_seconds: float):
        self.name = name
        self._output = output
        self._delay_seconds = delay_seconds

    def run(self, text: str) -> AgentResponse:
        time.sleep(self._delay_seconds)
        return AgentResponse(input=text, output=self._output, model="stub-model", agent=self.name)


class StubAgent:
    """Minimal stand-in with the same .run(text) -> AgentResponse shape as
    a real Agent/ToolAgent, without needing a real LLM call per stub."""

    def __init__(self, name: str, output: str, tool_calls: list[str] | None = None):
        self.name = name
        self._output = output
        self._tool_calls = tool_calls or []

    def run(self, text: str) -> AgentResponse:
        return AgentResponse(
            input=text, output=self._output, model="stub-model",
            agent=self.name, tool_calls=self._tool_calls,
        )


# --- MultiAgentPlanner ---

def test_plan_single_agent():
    llm = ScriptedProvider(['{"agents": ["research"], "mode": "SINGLE", "reasoning": "just a lookup"}'])
    planner = MultiAgentPlanner(llm)

    plan = planner.plan("Explain RAG.")

    assert plan.mode == CoordinationMode.SINGLE
    assert plan.agents == [AgentName.RESEARCH]
    assert plan.needs_coordination is False


def test_plan_sequential_multi_agent():
    llm = ScriptedProvider(
        ['{"agents": ["research", "analysis", "planning"], "mode": "SEQUENTIAL", '
         '"reasoning": "planning needs the analysis which needs the research"}']
    )
    planner = MultiAgentPlanner(llm)

    plan = planner.plan("Research Kubernetes, compare it to ECS, then plan adoption.")

    assert plan.mode == CoordinationMode.SEQUENTIAL
    assert plan.agents == [AgentName.RESEARCH, AgentName.ANALYSIS, AgentName.PLANNING]
    assert plan.needs_coordination is True


def test_plan_parallel_multi_agent():
    llm = ScriptedProvider(
        ['{"agents": ["research", "analysis"], "mode": "PARALLEL", '
         '"reasoning": "the two are independent asks"}']
    )
    planner = MultiAgentPlanner(llm)

    plan = planner.plan("Give me a research summary of RAG and a separate risk analysis.")

    assert plan.mode == CoordinationMode.PARALLEL
    assert plan.needs_coordination is True


def test_plan_empty_input_raises():
    planner = MultiAgentPlanner(ScriptedProvider([]))

    with pytest.raises(ValueError):
        planner.plan("")


def test_plan_malformed_output_raises_planning_error():
    planner = MultiAgentPlanner(ScriptedProvider(["not json", "still not json", "nope"]))

    with pytest.raises(MultiAgentPlanningError):
        planner.plan("Some request.")


# --- MultiAgentCoordinator ---

def test_sequential_coordination_chains_agent_outputs():
    research = StubAgent("research_agent", "Kubernetes is a container orchestrator.")
    analysis = StubAgent("analyst_agent", "ECS is simpler; Kubernetes is more flexible.")
    planning = StubAgent("planner_agent", "Week 1: pilot Kubernetes. Week 2: migrate.")

    llm = ScriptedProvider([])  # synthesis LLM not called in sequential mode
    coordinator = MultiAgentCoordinator(
        llm, {AgentName.RESEARCH: research, AgentName.ANALYSIS: analysis, AgentName.PLANNING: planning}
    )
    plan = MultiAgentPlan(
        agents=[AgentName.RESEARCH, AgentName.ANALYSIS, AgentName.PLANNING],
        mode=CoordinationMode.SEQUENTIAL, reasoning="test",
    )

    result = coordinator.run("Research K8s, compare to ECS, plan adoption.", plan)

    assert result.output == "Week 1: pilot Kubernetes. Week 2: migrate."  # final agent's output
    assert result.agent == "multi_agent:sequential:research_agent+analyst_agent+planner_agent"


def test_parallel_coordination_synthesizes_outputs():
    research = StubAgent("research_agent", "RAG combines retrieval with generation.")
    analysis = StubAgent("analyst_agent", "Main risk: retrieval quality bottlenecks the whole system.")

    llm = ScriptedProvider(["Combined: RAG explained, with retrieval-quality risk noted."])
    coordinator = MultiAgentCoordinator(llm, {AgentName.RESEARCH: research, AgentName.ANALYSIS: analysis})
    plan = MultiAgentPlan(agents=[AgentName.RESEARCH, AgentName.ANALYSIS], mode=CoordinationMode.PARALLEL, reasoning="test")

    result = coordinator.run("Research RAG and separately assess its risk.", plan)

    assert result.output == "Combined: RAG explained, with retrieval-quality risk noted."
    assert result.agent == "multi_agent:parallel:research_agent+analyst_agent"


def test_sequential_combines_tool_calls_from_all_agents():
    research = StubAgent("research_agent", "output1", tool_calls=["retrieve"])
    analysis = StubAgent("analyst_agent", "output2", tool_calls=["calculator"])

    coordinator = MultiAgentCoordinator(ScriptedProvider([]), {AgentName.RESEARCH: research, AgentName.ANALYSIS: analysis})
    plan = MultiAgentPlan(agents=[AgentName.RESEARCH, AgentName.ANALYSIS], mode=CoordinationMode.SEQUENTIAL, reasoning="test")

    result = coordinator.run("some request", plan)

    assert result.tool_calls == ["retrieve", "calculator"]


def test_parallel_coordination_actually_runs_concurrently():
    """Real regression guard for the bug found while investigating 'AI Cost
    & Latency Engineering': _run_parallel() used to be a plain list
    comprehension (each agent run one after another despite the PARALLEL
    name). Three agents each sleeping 0.3s should finish in ~0.3-0.6s if
    genuinely concurrent, not ~0.9s+ if sequential."""
    research = SlowStubAgent("research_agent", "r", delay_seconds=0.3)
    analysis = SlowStubAgent("analyst_agent", "a", delay_seconds=0.3)
    planning = SlowStubAgent("planner_agent", "p", delay_seconds=0.3)

    llm = ScriptedProvider(["combined"])
    coordinator = MultiAgentCoordinator(
        llm, {AgentName.RESEARCH: research, AgentName.ANALYSIS: analysis, AgentName.PLANNING: planning}
    )
    plan = MultiAgentPlan(
        agents=[AgentName.RESEARCH, AgentName.ANALYSIS, AgentName.PLANNING],
        mode=CoordinationMode.PARALLEL, reasoning="test",
    )

    started = time.monotonic()
    result = coordinator.run("some request", plan)
    elapsed = time.monotonic() - started

    assert elapsed < 0.7  # would be >=0.9s if sequential
    assert result.output == "combined"
