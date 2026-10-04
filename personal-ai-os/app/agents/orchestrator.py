from pydantic import BaseModel

from app.agents.analyst_agent import AnalystAgent
from app.agents.base import AgentResponse
from app.agents.multi_agent_coordinator import (
    AgentName,
    MultiAgentCoordinator,
    MultiAgentPlanner,
    MultiAgentPlanningError,
    might_need_multiple_agents,
)
from app.agents.planner_agent import PlannerAgent
from app.agents.research_agent import ResearchAgent
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.base import LLMProvider
from app.retrieval.vector_search import VectorStore
from app.routing.classifier import TaskType
from app.routing.unified_router import UnifiedClassification, UnifiedRouter, UnifiedRoutingError

_TASK_TYPE_TO_AGENT_NAME = {
    TaskType.RESEARCH: AgentName.RESEARCH,
    TaskType.ANALYSIS: AgentName.ANALYSIS,
    TaskType.PLANNING: AgentName.PLANNING,
}


class ClarificationNeeded(BaseModel):
    input: str
    message: str


class Orchestrator:
    """Combines what were previously two separate, disconnected routers
    (DomainRouter and TaskClassifier) via UnifiedRouter, then dispatches to
    the same 3 generic agents as before -- now domain-aware AND all 3 with
    real tool access (previously only ResearchAgent could call tools -- a
    real asymmetry the user pointed out). Domain workflows needing a real
    stored object a chat message can't manufacture (analyze_portfolio needs
    a Portfolio, evaluate_answer needs an Exercise) are NOT invoked here and
    remain separate. The text-only/retriever-groundable ones (analyze_jd,
    draft_prd, analyze_feedback) ARE bridged in as real tools any of the 3
    agents can call (see app/tools/domain_workflow_tools.py) -- confirmed
    scope decision with the user.

    Multi-agent orchestration (user's ask: "some inputs will require all
    3... pattern will not be sequential, will depend on the input"): before
    dispatching to a single agent, a cheap MultiAgentPlanner call decides
    whether this specific request genuinely needs more than one agent, and
    if so whether they run SEQUENTIAL (each feeding the next) or PARALLEL
    (independent, then synthesized) -- a real per-input decision, not a
    fixed pipeline. Most requests are SINGLE and keep the original fast
    path (1 router call + 1 agent); only genuinely multi-agent requests pay
    for the extra planning call and extra agent runs."""

    def __init__(
        self, llm: LLMProvider, retrieval_store: VectorStore | None = None,
        on_tool_call=None, on_classified=None,
        secure_retriever: SecureRetriever | None = None, requester_id: str | None = None,
        requester_tenant_id: str | None = None, on_multi_agent_planned=None,
        mcp_tools: list | None = None, on_tool_error=None, agent_llm: LLMProvider | None = None,
        policy_engine=None,
    ):
        # retrieval_store/secure_retriever/requester_* are all optional and
        # additive: passing none of them (the default, matching every
        # existing caller's behavior exactly) constructs all 3 agents with
        # only the calculator tool, same as ResearchAgent's original
        # behavior before this change. on_tool_call is forwarded to all 3
        # agents (each now has a real tool loop) for callers that need real
        # tool-call I/O visibility. on_classified (optional, called as
        # on_classified(UnifiedClassification)) exposes the router's own
        # decision to a caller -- handle()'s return type (AgentResponse |
        # ClarificationNeeded) doesn't carry the classification itself, so
        # callers that need it (e.g. scripts/trace_request.py) observe it
        # via this hook instead of Orchestrator's return type changing for
        # everyone. on_multi_agent_planned (optional, called as
        # on_multi_agent_planned(MultiAgentPlan)) exposes the multi-agent
        # planning decision the same way. mcp_tools (optional): real Tool
        # instances discovered from a connected MCP server (see
        # app/tools/mcp_tool.py), forwarded to all 3 agents identically to
        # every other optional tool dependency. on_tool_error (optional,
        # called as on_tool_error(tool_name, args, error_message)) mirrors
        # on_tool_call for the real-bug fix in ToolAgent: a tool raising
        # ToolError is now caught and recorded instead of crashing the
        # whole request; this hook exposes that to callers that need
        # failure visibility (e.g. scripts/trace_request.py). agent_llm
        # (optional, real model-routing hook): when given, the 3 agents'
        # own generation calls use THIS provider instead of llm, while
        # UnifiedRouter/MultiAgentPlanner's classification/planning calls
        # always keep using llm -- classification never benefits from a
        # stronger model and shouldn't burn a routed tier's real quota on
        # every single request. Defaults to llm (identical behavior to
        # every existing caller) when not given. This is the real
        # integration point for app/routing/model_router.py's ModelRouter.
        # policy_engine (optional, real governance hook): when given, ALL 3
        # agents' tool calls go through it -- real risk classification,
        # real sandboxed execution (app/platform/sandbox.py), and a real
        # human-approval gate for WRITE/ACT-risk tools -- instead of
        # calling tool.call() directly. A real, previously-undisclosed gap
        # this closes: the live chat-agent path never went through
        # PolicyEngine at all before this, only separate domain-workflow
        # code did. Defaults to None (every existing caller's identical,
        # unsandboxed, ungoverned behavior) when not given.
        self._llm = llm  # exposed via the llm property below -- e.g. VoiceSession
        # needs the same real LLMProvider for its own memory-related calls
        # without reaching into a private attribute.
        self._router = UnifiedRouter(llm)
        self._multi_agent_planner = MultiAgentPlanner(llm)
        self._on_classified = on_classified
        self._on_multi_agent_planned = on_multi_agent_planned
        effective_agent_llm = agent_llm or llm
        agent_kwargs = dict(
            store=retrieval_store, on_tool_call=on_tool_call, on_tool_error=on_tool_error,
            secure_retriever=secure_retriever, requester_id=requester_id,
            requester_tenant_id=requester_tenant_id, mcp_tools=mcp_tools,
            policy_engine=policy_engine,
        )
        self._agents = {
            TaskType.RESEARCH: ResearchAgent(effective_agent_llm, **agent_kwargs),
            TaskType.ANALYSIS: AnalystAgent(effective_agent_llm, **agent_kwargs),
            TaskType.PLANNING: PlannerAgent(effective_agent_llm, **agent_kwargs),
        }
        agents_by_name = {
            task_type_to_name: self._agents[task_type]
            for task_type, task_type_to_name in _TASK_TYPE_TO_AGENT_NAME.items()
        }
        self._coordinator = MultiAgentCoordinator(effective_agent_llm, agents_by_name)

    @property
    def llm(self) -> LLMProvider:
        """The same LLMProvider this Orchestrator was constructed with --
        exposed so a caller wrapping Orchestrator (e.g. VoiceSession,
        ConversationSession) can reuse the identical provider for its own
        real LLM calls (memory classification, summarization) without
        reaching into a private attribute or requiring its own separate
        constructor argument."""
        return self._llm

    def handle(self, text: str) -> AgentResponse | ClarificationNeeded:
        if not text or not text.strip():
            raise ValueError("Input text must not be empty.")

        multi_agent_plan = None
        if might_need_multiple_agents(text):
            # Cheap, free (no LLM call) heuristic gate, confirmed with the
            # user: paying for a real planning call on every single
            # request -- including obviously-simple ones -- was an
            # unacceptable cost increase. Only requests that plausibly
            # need coordination pay for this real LLM call at all.
            try:
                multi_agent_plan = self._multi_agent_planner.plan(text)
            except MultiAgentPlanningError:
                multi_agent_plan = None  # degrade to the normal single-agent path below

            if self._on_multi_agent_planned and multi_agent_plan is not None:
                self._on_multi_agent_planned(multi_agent_plan)

            if multi_agent_plan is not None and multi_agent_plan.needs_coordination:
                return self._coordinator.run(text, multi_agent_plan)

        try:
            classification = self._router.route(text)
        except UnifiedRoutingError as exc:
            return ClarificationNeeded(input=text, message=f"Could not classify this request: {exc}")

        if self._on_classified:
            self._on_classified(classification)

        if classification.task_type == TaskType.UNCLEAR:
            return ClarificationNeeded(
                input=text,
                message=(
                    "I'm not sure what you'd like me to do. Could you clarify "
                    "whether this is a research, analysis, or planning request?"
                ),
            )

        agent = self._agents[classification.task_type]
        prompted_text = self._with_domain_context(text, classification)
        return agent.run(prompted_text)

    @staticmethod
    def _with_domain_context(text: str, classification: UnifiedClassification) -> str:
        """Prepends a domain hint to the literal text the agent sees, rather
        than changing Agent/ToolAgent's run() signature (which would touch
        every agent and every existing test). GENERAL (classification.domain
        is None) adds no hint at all -- most requests don't belong to a
        Phase 3 domain, and forcing a label into the prompt for those would
        just be noise."""
        if classification.domain is None:
            return text
        domain_names = "+".join(d.value for d in classification.all_domains)
        return f"[Context: this request has been classified under the {domain_names} domain.]\n\n{text}"
