from pydantic import BaseModel

from app.agents.analyst_agent import AnalystAgent
from app.agents.base import AgentResponse
from app.agents.planner_agent import PlannerAgent
from app.agents.research_agent import ResearchAgent
from app.providers.base import LLMProvider
from app.retrieval.vector_search import VectorStore
from app.routing.classifier import TaskType
from app.routing.unified_router import UnifiedClassification, UnifiedRouter, UnifiedRoutingError


class ClarificationNeeded(BaseModel):
    input: str
    message: str


class Orchestrator:
    """Combines what were previously two separate, disconnected routers
    (DomainRouter and TaskClassifier) via UnifiedRouter, then dispatches to
    the same 3 generic agents as before -- now domain-aware. Domain
    workflows (app/domains/{career,pm,finance,learning}/*, e.g. analyze_jd,
    draft_prd, analyze_portfolio) are NOT invoked here: they need specific
    typed inputs (a Portfolio object, an Exercise object, extracted JD text)
    that a plain chat message doesn't provide, and remain separate, invoked
    explicitly elsewhere with their real structured inputs (confirmed scope
    decision with the user)."""

    def __init__(
        self, llm: LLMProvider, retrieval_store: VectorStore | None = None,
        on_tool_call=None, on_classified=None,
    ):
        # retrieval_store is optional and additive: passing None (the
        # default, matching every existing caller's behavior exactly)
        # constructs ResearchAgent without a retrieve tool, same as before.
        # Passing a real VectorStore lets ResearchAgent's retrieve tool
        # actually ground answers in indexed documents. on_tool_call is
        # forwarded to ResearchAgent (the only agent here with a tool loop)
        # for callers that need real tool-call I/O visibility. on_classified
        # (optional, called as on_classified(UnifiedClassification)) exposes
        # the router's own decision to a caller -- handle()'s return type
        # (AgentResponse | ClarificationNeeded) doesn't carry the
        # classification itself, so callers that need it (e.g.
        # scripts/trace_request.py) observe it via this hook instead of
        # Orchestrator's return type changing for everyone.
        self._router = UnifiedRouter(llm)
        self._on_classified = on_classified
        self._agents = {
            TaskType.RESEARCH: ResearchAgent(llm, store=retrieval_store, on_tool_call=on_tool_call),
            TaskType.ANALYSIS: AnalystAgent(llm),
            TaskType.PLANNING: PlannerAgent(llm),
        }

    def handle(self, text: str) -> AgentResponse | ClarificationNeeded:
        if not text or not text.strip():
            raise ValueError("Input text must not be empty.")

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
