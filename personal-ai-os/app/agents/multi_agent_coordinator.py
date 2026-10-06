"""Multi-agent coordination for inputs that genuinely need more than one of
Research/Analyst/Planner -- per the user's explicit ask: "we need to think
of multi agent orchestration between research agent, analyst, planner agent
as some inputs will require all 3" and "pattern will not be sequential,
will depend on the input."

Design (confirmed with the user): a NEW coordinator, invoked only when
genuinely needed -- most requests keep going through Orchestrator's existing
fast single-agent path (1 router call + 1 agent). This module adds one
cheap extra classification call (MultiAgentPlanner) that decides, per input:
  - Does this need just one agent, or more than one?
  - If more than one: which agents, and are they independent (PARALLEL,
    each given the same input, then synthesized) or do they build on each
    other (SEQUENTIAL, each agent's output feeds the next as context)?
That decision is genuinely per-input (an LLM call), not a fixed pipeline --
the user explicitly rejected always-sequential.

Real example this is meant to handle: "Research the pros/cons of
Kubernetes, compare it against ECS for our use case, and give me a 30-day
adoption plan" genuinely needs ResearchAgent (gather facts) -> AnalystAgent
(compare, grounded in that research) -> PlannerAgent (plan, grounded in
that comparison) -- a real SEQUENTIAL case. A request like "Give me both a
research summary of RAG and a completely separate risk analysis of using
it" is better served PARALLEL (the two aren't inputs to each other) then
combined.
"""

from concurrent.futures import ThreadPoolExecutor
from enum import Enum

from pydantic import BaseModel

from app.agents.base import AgentResponse
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator, StructuredOutputError

# Cheap, no-LLM-call heuristic deciding whether it's even worth asking the
# (real, paid) MultiAgentPlanner question at all. Confirmed with the user:
# every request paying for an extra LLM call was an unacceptable cost
# increase for the common single-agent case, so this gate runs first and
# is free. Deliberately conservative (a false positive just costs one wasted
# planning call that will itself say SINGLE; a false negative silently
# skips real multi-agent coordination, which is the worse failure mode) --
# tuned toward casting a slightly wide net rather than a narrow one.
_MULTI_AGENT_SIGNAL_WORDS = (
    " then ", " and then ", " after that ", " once you", " once that",
    " next, ", " and also ", " as well as ", " followed by ",
)
_MIN_WORD_COUNT_FOR_CONSIDERATION = 18


def might_need_multiple_agents(text: str) -> bool:
    """True if this input is plausibly asking for more than one kind of
    work (research + analysis + planning, etc.) and therefore worth the
    real MultiAgentPlanner LLM call. False means: skip straight to the
    normal single-agent path, no extra call at all."""
    lowered = f" {text.lower()} "
    if any(signal in lowered for signal in _MULTI_AGENT_SIGNAL_WORDS):
        return True
    return len(text.split()) >= _MIN_WORD_COUNT_FOR_CONSIDERATION

MULTI_AGENT_PLAN_PROMPT = """Decide how many of the following specialist agents
this request genuinely needs, and in what order.

Agents:
- research: explains a topic, looks things up, grounds facts
- analysis: compares options, evaluates tradeoffs, makes a recommendation
- planning: breaks a goal into a concrete sequenced plan

Most requests need only ONE agent. Only select more than one when the
request genuinely asks for multiple distinct kinds of work (e.g. "research
X, then compare X vs Y, then give me a plan to adopt the winner" needs all
three). Do not invent extra agents just because a request is complex --
complexity alone is not multi-agent need.

If more than one agent is needed, decide:
- SEQUENTIAL: a later agent's work genuinely depends on an earlier agent's
  output (e.g. planning needs the analysis's conclusion)
- PARALLEL: the agents' work is independent -- neither needs the other's
  output, they just both apply to the same request

Respond with ONLY a JSON object:
{{"agents": ["research" | "analysis" | "planning", ...], "mode": "SEQUENTIAL" | "PARALLEL" | "SINGLE", "reasoning": "<why>"}}

If only one agent is needed, respond with mode "SINGLE" and exactly one agent in the list.

User request: {text}
"""


class CoordinationMode(str, Enum):
    SINGLE = "SINGLE"
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"


class AgentName(str, Enum):
    RESEARCH = "research"
    ANALYSIS = "analysis"
    PLANNING = "planning"


class MultiAgentPlan(BaseModel):
    agents: list[AgentName]
    mode: CoordinationMode
    reasoning: str

    @property
    def needs_coordination(self) -> bool:
        return self.mode != CoordinationMode.SINGLE and len(self.agents) > 1


class MultiAgentPlanningError(Exception):
    pass


class MultiAgentPlanner:
    """The one extra, real LLM call: decides whether a request needs
    multiple agents and how they should be coordinated. Deliberately cheap
    and separate from UnifiedRouter's domain/task-type classification --
    this answers a different question ('how many agents, what shape') than
    UnifiedRouter answers ('which single agent's specialty fits best')."""

    def __init__(self, llm: LLMProvider):
        self._generator = RepairableGenerator(llm, MultiAgentPlan)

    def plan(self, text: str) -> MultiAgentPlan:
        if not text or not text.strip():
            raise ValueError("Input text must not be empty.")
        try:
            return self._generator.generate(MULTI_AGENT_PLAN_PROMPT.format(text=text))
        except StructuredOutputError as exc:
            raise MultiAgentPlanningError(str(exc)) from exc


SYNTHESIS_PROMPT = """Multiple specialist agents each produced a response to
the same user request, independently (not building on each other). Combine
their outputs into ONE coherent answer for the user. Do not drop any
agent's substantive content; resolve only presentational overlap/duplication.

User request: {text}

{agent_outputs}

Respond with the combined answer as plain text (not JSON).
"""


class MultiAgentCoordinator:
    """Actually runs the agents a MultiAgentPlan calls for. Constructed with
    the already-built agent instances (same ones Orchestrator already has --
    this class does not build its own agents, so tool wiring/domain context
    stays identical to the single-agent path)."""

    def __init__(self, llm: LLMProvider, agents_by_name: dict[AgentName, object]):
        self._llm = llm
        self._agents = agents_by_name

    def run(self, text: str, plan: MultiAgentPlan) -> AgentResponse:
        if plan.mode == CoordinationMode.SEQUENTIAL:
            return self._run_sequential(text, plan)
        return self._run_parallel(text, plan)

    def _run_sequential(self, text: str, plan: MultiAgentPlan) -> AgentResponse:
        current_text = text
        responses: list[AgentResponse] = []
        for agent_name in plan.agents:
            agent = self._agents[agent_name]
            response = agent.run(current_text)
            responses.append(response)
            # Next agent gets the previous agent's real output as context,
            # prepended to the ORIGINAL request -- so it still knows what
            # the user actually asked, not just the prior agent's answer.
            current_text = (
                f"[Context from {response.agent}'s prior analysis:]\n{response.output}\n\n"
                f"[Original request:]\n{text}"
            )
        return self._combined_response(text, plan, responses, final_output=responses[-1].output)

    def _run_parallel(self, text: str, plan: MultiAgentPlan) -> AgentResponse:
        # Real fix (found while investigating "AI Cost & Latency Engineering" --
        # this used to be a plain list comprehension, i.e. each agent run
        # sequentially despite the PARALLEL name/label). ThreadPoolExecutor.map
        # actually dispatches every agent's .run() concurrently -- real wall-clock
        # benefit, proven in tests/test_multi_agent_coordinator.py by agents with
        # artificial delay finishing in ~max(delays), not ~sum(delays). map()
        # still returns results in plan.agents order, so _combined_response's
        # agent_label/tool_call ordering is unchanged. Each agent only touches its
        # own self._llm (no shared mutable state across agents), so this is safe.
        with ThreadPoolExecutor(max_workers=len(plan.agents)) as executor:
            responses = list(executor.map(lambda name: self._agents[name].run(text), plan.agents))
        agent_outputs = "\n\n".join(f"--- {r.agent} ---\n{r.output}" for r in responses)
        synthesis_prompt = SYNTHESIS_PROMPT.format(text=text, agent_outputs=agent_outputs)
        combined_output = self._llm.generate(synthesis_prompt)
        return self._combined_response(text, plan, responses, final_output=combined_output)

    def _combined_response(
        self, text: str, plan: MultiAgentPlan, responses: list[AgentResponse], final_output: str
    ) -> AgentResponse:
        agent_label = f"multi_agent:{plan.mode.value.lower()}:" + "+".join(r.agent for r in responses)
        all_tool_calls = [call for r in responses for call in r.tool_calls]
        return AgentResponse(
            input=text, output=final_output, model=self._llm.model_name,
            agent=agent_label, tool_calls=all_tool_calls, stop_reason="task_completed",
        )
