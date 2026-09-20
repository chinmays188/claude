from enum import Enum

from pydantic import BaseModel

from app.proactive.attention import ScoredSignal
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

DECISION_PROMPT = """A signal was surfaced by the attention engine. Decide what
kind of response it warrants. Do not invent context beyond what's given.

Signal: {title}
Description: {description}
Attention score: {score}

Respond with ONLY a JSON object:
{{"response_type": "NO_ACTION" | "NOTIFY_ONLY" | "PROPOSE_PLAN" | "ESCALATE", "reasoning": "<why>"}}
"""


class ResponseType(str, Enum):
    NO_ACTION = "NO_ACTION"  # signal noted but not worth surfacing at all
    NOTIFY_ONLY = "NOTIFY_ONLY"  # surface to the user, no action plan needed
    PROPOSE_PLAN = "PROPOSE_PLAN"  # warrants a concrete action plan (Milestone 36)
    ESCALATE = "ESCALATE"  # high-severity, should interrupt rather than wait for a daily brief


class Decision(BaseModel):
    signal_id: str
    response_type: ResponseType
    reasoning: str


class _RawDecision(BaseModel):
    """What the LLM is actually asked to produce — no signal_id, since the
    model has no business inventing or echoing back an id; the real Decision
    is assembled from this plus the caller's own signal_id."""

    response_type: ResponseType
    reasoning: str


class DecisionEngine:
    """Milestone 38: 'Personal Decision Engine.' The one component whose sole
    job is to decide HOW MUCH response a given signal deserves — never to act
    itself. This is the concrete embodiment of Phase 4's core rule: AI should
    not directly execute consequential actions. A DecisionEngine's output is
    always just a Decision, routed elsewhere (a plan proposer, a notifier) to
    actually do anything."""

    def __init__(self, llm: LLMProvider):
        self._llm = llm

    def decide(self, scored_signal: ScoredSignal) -> Decision:
        generator = RepairableGenerator(self._llm, _RawDecision)
        prompt = DECISION_PROMPT.format(
            title=scored_signal.signal.title, description=scored_signal.signal.description,
            score=scored_signal.attention_score,
        )
        raw = generator.generate(prompt)
        return Decision(signal_id=scored_signal.signal.signal_id, response_type=raw.response_type, reasoning=raw.reasoning)
