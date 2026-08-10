from app.evaluation.llm_judge import judge_response
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_judge_returns_all_dimensions():
    llm = ScriptedProvider(
        [
            '{"correctness": 0.9, "completeness": 0.85, "groundedness": 0.95, '
            '"citation_quality": 0.9, "instruction_following": 0.95, "overall": 0.91}'
        ]
    )

    score = judge_response(
        llm, user_input="Explain RAG.", expected_behavior="definition + example",
        agent_output="RAG is...",
    )

    assert score.correctness == 0.9
    assert score.overall == 0.91


def test_judge_uses_repair_on_malformed_output():
    llm = ScriptedProvider(
        [
            "not json",
            '{"correctness": 0.8, "completeness": 0.8, "groundedness": 0.8, '
            '"citation_quality": 0.8, "instruction_following": 0.8, "overall": 0.8}',
        ]
    )

    score = judge_response(llm, user_input="x", expected_behavior="y", agent_output="z")

    assert score.overall == 0.8
