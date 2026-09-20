import pytest

from app.domains.learning.evaluator import evaluate_answer, identify_knowledge_gap
from app.domains.learning.models import Exercise
from app.evaluation.learning_eval import check_evaluation_scores_in_range
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _exercise() -> Exercise:
    return Exercise(concept="Docker", question="What does a Dockerfile do?", expected_answer_summary="Defines how to build an image.")


def test_evaluate_answer_returns_all_five_dimensions():
    llm = ScriptedProvider(
        ['{"conceptual_understanding": 8, "technical_depth": 6, "application": 7, "system_thinking": 8, '
         '"pm_translation": 9, "feedback": "Good grasp, could go deeper on layers."}']
    )

    evaluation = evaluate_answer(llm, _exercise(), "A Dockerfile defines the steps to build an image.")

    assert evaluation.conceptual_understanding == 8
    assert evaluation.pm_translation == 9
    assert check_evaluation_scores_in_range(evaluation).passed


def test_evaluate_answer_rejects_empty_answer():
    llm = ScriptedProvider([])

    with pytest.raises(ValueError):
        evaluate_answer(llm, _exercise(), "")


def test_identify_knowledge_gap_returns_gaps():
    llm = ScriptedProvider(
        ['{"gaps": [{"concept": "Docker layers", "description": "Did not mention layer caching.", "severity": 0.6}]}']
    )
    evaluation_placeholder = evaluate_answer_stub()

    gaps = identify_knowledge_gap(llm, _exercise(), "some answer", evaluation_placeholder)

    assert len(gaps) == 1
    assert gaps[0].concept == "Docker layers"


def test_identify_knowledge_gap_returns_empty_list_when_no_gaps():
    llm = ScriptedProvider(['{"gaps": []}'])
    evaluation_placeholder = evaluate_answer_stub()

    gaps = identify_knowledge_gap(llm, _exercise(), "strong answer", evaluation_placeholder)

    assert gaps == []


def evaluate_answer_stub():
    from app.domains.learning.models import AnswerEvaluation

    return AnswerEvaluation(
        conceptual_understanding=7, technical_depth=7, application=7, system_thinking=7,
        pm_translation=7, feedback="ok",
    )


def test_check_scores_out_of_range_fails():
    bad_evaluation = evaluate_answer_stub()
    bad_evaluation.conceptual_understanding = 15  # bypass Pydantic validation via direct mutation

    result = check_evaluation_scores_in_range(bad_evaluation)

    assert not result.passed
