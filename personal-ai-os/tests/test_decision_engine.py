from app.proactive.attention import ScoredSignal
from app.proactive.decision_engine import DecisionEngine, ResponseType
from app.proactive.triggers import Signal
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _scored(title="Urgent issue") -> ScoredSignal:
    signal = Signal(owner_id="alice", trigger_name="urgent_email", title=title, description="d", source_event_id="e1")
    return ScoredSignal(signal=signal, attention_score=0.9, reason="r")


def test_decide_returns_response_type_and_reasoning():
    llm = ScriptedProvider(['{"response_type": "ESCALATE", "reasoning": "High-severity, time-sensitive."}'])
    engine = DecisionEngine(llm)

    decision = engine.decide(_scored())

    assert decision.response_type == ResponseType.ESCALATE
    assert decision.reasoning


def test_decide_preserves_real_signal_id_not_llm_echo():
    llm = ScriptedProvider(['{"response_type": "NOTIFY_ONLY", "reasoning": "Worth noting."}'])
    engine = DecisionEngine(llm)
    scored = _scored()

    decision = engine.decide(scored)

    assert decision.signal_id == scored.signal.signal_id
