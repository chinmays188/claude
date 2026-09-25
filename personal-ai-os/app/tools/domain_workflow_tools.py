"""Bridge tools wrapping domain workflow functions
(app/domains/{career,pm}/*.py) so any ToolAgent (Research/Analyst/Planner)
can invoke them from a chat message, instead of those workflows only being
reachable by calling their Python functions directly with pre-built typed
inputs.

Scope decided explicitly with the user: only workflows that take a plain
string (or a string + a SecureRetriever the agent is already configured
with) are bridged here. Workflows needing a real stored object a chat
message can't manufacture -- analyze_portfolio(portfolio: Portfolio),
evaluate_answer(exercise: Exercise, answer: str) -- are explicitly OUT of
scope for this pass and stay reachable only via their own Python functions,
called with real objects from their own stores.

analyze_jd and draft_prd both need a SecureRetriever to ground their output
in the user's own documents (checked by reading the actual functions, not
assumed) -- these tools reuse the same retrieval_store an agent may already
have wired in for the plain 'retrieve' tool (e.g. via
scripts/trace_request.py's --index-file), rather than requiring a second,
separate index."""

from pydantic import BaseModel

from app.domains.career.jd_analysis import analyze_jd
from app.domains.pm.feedback_intelligence import analyze_feedback
from app.domains.pm.prd import draft_prd
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.base import LLMProvider
from app.tools.base import Tool, ToolError


class AnalyzeFeedbackArgs(BaseModel):
    feedback_items: list[str]


class AnalyzeFeedbackTool(Tool):
    name = "analyze_feedback"
    description = (
        "Analyze a list of raw customer/stakeholder feedback strings: clusters "
        "them into themes, estimates frequency/severity, flags critical issues, "
        "and recommends actions. Use this when the user gives you multiple "
        "pieces of feedback to make sense of, not for a single freeform question."
    )
    permissions = ["read:pm_workflows"]
    retry_safe = True
    args_schema = AnalyzeFeedbackArgs

    def __init__(self, llm: LLMProvider):
        self._llm = llm

    def run(self, args: AnalyzeFeedbackArgs) -> str:
        try:
            result = analyze_feedback(self._llm, args.feedback_items)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        return result.model_dump_json()


class AnalyzeJdArgs(BaseModel):
    jd_text: str


class AnalyzeJdTool(Tool):
    name = "analyze_jd"
    description = (
        "Analyze a job description against the candidate's own retrieved resume/"
        "achievement documents: fit scores, major gaps, recommended resume "
        "changes, interview risks. Requires documents to already be indexed "
        "(e.g. via --index-file) -- returns an error if none are available. Use "
        "this when the user pastes a job description and asks about fit."
    )
    permissions = ["read:career_workflows", "read:retrieval"]
    retry_safe = True
    args_schema = AnalyzeJdArgs

    def __init__(self, llm: LLMProvider, secure_retriever: SecureRetriever, requester_id: str, requester_tenant_id: str):
        self._llm = llm
        self._retriever = secure_retriever
        self._requester_id = requester_id
        self._requester_tenant_id = requester_tenant_id

    def run(self, args: AnalyzeJdArgs) -> str:
        try:
            result = analyze_jd(
                self._llm, args.jd_text, self._retriever,
                requester_id=self._requester_id, requester_tenant_id=self._requester_tenant_id,
            )
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        return result.model_dump_json()


class DraftPrdArgs(BaseModel):
    idea: str


class DraftPrdTool(Tool):
    name = "draft_prd"
    description = (
        "Draft a PRD (problem statement, customer context, hypothesis, solution, "
        "metrics, experiment) for a product idea, grounded in retrieved existing "
        "product docs when available. Requires documents to already be indexed "
        "(e.g. via --index-file) -- works with no context if none are indexed, "
        "just without grounding. Use this when the user describes a product idea "
        "and asks for a PRD, not for general product-strategy questions."
    )
    permissions = ["read:pm_workflows", "read:retrieval"]
    retry_safe = True
    args_schema = DraftPrdArgs

    def __init__(self, llm: LLMProvider, secure_retriever: SecureRetriever, requester_id: str, requester_tenant_id: str):
        self._llm = llm
        self._retriever = secure_retriever
        self._requester_id = requester_id
        self._requester_tenant_id = requester_tenant_id

    def run(self, args: DraftPrdArgs) -> str:
        try:
            result = draft_prd(
                self._llm, args.idea, self._retriever,
                requester_id=self._requester_id, requester_tenant_id=self._requester_tenant_id,
            )
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        return result.model_dump_json()
