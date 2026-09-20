from app.evaluation.personal_metrics import score_actionability_and_trust
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_score_returns_both_dimensions():
    llm = ScriptedProvider(
        ['{"actionability": 0.9, "trustworthiness": 0.8, "reasoning": "Concrete next step given, grounded in evidence."}']
    )

    score = score_actionability_and_trust(llm, "What should I focus on today?", "Finish the RAG milestone first.")

    assert score.actionability == 0.9
    assert score.trustworthiness == 0.8
    assert score.reasoning


def test_score_uses_repair_on_malformed_output():
    llm = ScriptedProvider(
        [
            "not json",
            '{"actionability": 0.5, "trustworthiness": 0.5, "reasoning": "ok"}',
        ]
    )

    score = score_actionability_and_trust(llm, "q", "a")

    assert score.actionability == 0.5
