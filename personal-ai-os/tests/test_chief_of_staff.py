from app.proactive.attention import AttentionEngine
from app.proactive.builtin_triggers import UrgentEmailTrigger
from app.proactive.chief_of_staff import ChiefOfStaffOrchestrator
from app.proactive.decision_engine import DecisionEngine
from app.proactive.events import Event, EventType
from app.proactive.triggers import TriggerEngine
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_process_produces_signals_and_decisions():
    llm = ScriptedProvider(['{"response_type": "NOTIFY_ONLY", "reasoning": "Worth flagging."}'])
    orchestrator = ChiefOfStaffOrchestrator(
        trigger_engine=TriggerEngine([UrgentEmailTrigger()]),
        attention_engine=AttentionEngine(),
        decision_engine=DecisionEngine(llm),
        llm=llm,
        available_tool_names=["send_email"],
    )
    event = Event(type=EventType.EMAIL_RECEIVED, owner_id="alice", payload={"category": "URGENT", "subject": "Server down"})

    result = orchestrator.process([event])

    assert len(result.scored_signals) == 1
    assert len(result.decisions) == 1
    assert result.proposed_plans == []  # NOTIFY_ONLY -> no plan proposed


def test_process_proposes_plan_when_decision_says_so():
    llm = ScriptedProvider(
        [
            '{"response_type": "PROPOSE_PLAN", "reasoning": "Needs a concrete plan."}',
            '{"steps": [{"tool_name": "send_email", "args": {"to": "a@b.com", "message": "hi"}, "description": "notify"}]}',
        ]
    )
    orchestrator = ChiefOfStaffOrchestrator(
        trigger_engine=TriggerEngine([UrgentEmailTrigger()]),
        attention_engine=AttentionEngine(),
        decision_engine=DecisionEngine(llm),
        llm=llm,
        available_tool_names=["send_email"],
    )
    event = Event(type=EventType.EMAIL_RECEIVED, owner_id="alice", payload={"category": "URGENT", "subject": "Server down"})

    result = orchestrator.process([event])

    assert len(result.proposed_plans) == 1
    assert result.proposed_plans[0].steps[0].tool_name == "send_email"


def test_process_no_matching_triggers_produces_no_signals():
    llm = ScriptedProvider([])
    orchestrator = ChiefOfStaffOrchestrator(
        trigger_engine=TriggerEngine([UrgentEmailTrigger()]),
        attention_engine=AttentionEngine(),
        decision_engine=DecisionEngine(llm),
        llm=llm,
        available_tool_names=[],
    )
    event = Event(type=EventType.EMAIL_RECEIVED, owner_id="alice", payload={"category": "FYI"})

    result = orchestrator.process([event])

    assert result.scored_signals == []
    assert result.decisions == []
