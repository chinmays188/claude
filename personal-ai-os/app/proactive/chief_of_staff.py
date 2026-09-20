from pydantic import BaseModel

from app.proactive.action_plans import ActionPlan, propose_plan
from app.proactive.attention import AttentionEngine, ScoredSignal
from app.proactive.decision_engine import Decision, DecisionEngine, ResponseType
from app.proactive.events import Event
from app.proactive.triggers import TriggerEngine
from app.providers.base import LLMProvider


class ChiefOfStaffResult(BaseModel):
    """One pass through the full Phase 4 loop for a batch of events:
    OBSERVE (events in) -> UNDERSTAND (triggers) -> PRIORITIZE (attention) ->
    PROPOSE (decision + optional plan). APPROVE/ACT/VERIFY happen later,
    outside this orchestrator, via PolicyEngine (Phase 2) — the orchestrator
    itself never executes anything."""

    scored_signals: list[ScoredSignal]
    decisions: list[Decision]
    proposed_plans: list[ActionPlan]


class ChiefOfStaffOrchestrator:
    """Milestone 41: composes Milestones 30-31, 36, and 38 into a single
    pipeline. Deliberately does not reimplement any of trigger evaluation,
    attention scoring, decision-making, or plan proposal — it only sequences
    calls to the components that already do each of those jobs."""

    def __init__(
        self, trigger_engine: TriggerEngine, attention_engine: AttentionEngine,
        decision_engine: DecisionEngine, llm: LLMProvider, available_tool_names: list[str],
    ):
        self._triggers = trigger_engine
        self._attention = attention_engine
        self._decisions = decision_engine
        self._llm = llm
        self._available_tool_names = available_tool_names

    def process(self, events: list[Event], min_attention_score: float = 0.0) -> ChiefOfStaffResult:
        raw_signals = [signal for event in events for signal in self._triggers.evaluate(event)]
        scored_signals = self._attention.rank(raw_signals, min_score=min_attention_score)

        decisions = [self._decisions.decide(scored) for scored in scored_signals]

        proposed_plans = []
        for scored, decision in zip(scored_signals, decisions):
            if decision.response_type == ResponseType.PROPOSE_PLAN:
                plan = propose_plan(
                    self._llm, owner_id=scored.signal.owner_id, signal_description=scored.signal.description,
                    available_tool_names=self._available_tool_names, triggered_by_signal_id=scored.signal.signal_id,
                )
                proposed_plans.append(plan)

        return ChiefOfStaffResult(scored_signals=scored_signals, decisions=decisions, proposed_plans=proposed_plans)
