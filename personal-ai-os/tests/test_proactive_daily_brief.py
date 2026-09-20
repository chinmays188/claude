from app.proactive.attention import ScoredSignal
from app.proactive.daily_brief import generate_proactive_daily_brief
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


def _scored(title="Goal at risk: X", trigger_name="goal_deadline_approaching", score=0.9) -> ScoredSignal:
    signal = Signal(owner_id="alice", trigger_name=trigger_name, title=title, description="desc", source_event_id="e1")
    return ScoredSignal(signal=signal, attention_score=score, reason="r")


def test_generates_priorities_from_ranked_signals():
    llm = ScriptedProvider(['{"priorities": ["Address goal at risk: X"]}'])
    scored_signal = _scored()

    brief = generate_proactive_daily_brief(llm, [scored_signal])

    assert brief.priorities == ["Address goal at risk: X"]
    assert brief.source_signal_ids == [scored_signal.signal.signal_id]


def test_empty_signals_returns_empty_brief_without_calling_llm():
    llm = ScriptedProvider([])

    brief = generate_proactive_daily_brief(llm, [])

    assert brief.priorities == []
    assert brief.source_signal_ids == []
