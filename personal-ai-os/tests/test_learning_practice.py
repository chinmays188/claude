import pytest

from app.domains.learning.practice import generate_exercise, generate_quiz
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_generate_exercise_returns_question():
    llm = ScriptedProvider(['{"concept": "Docker", "question": "What does a Dockerfile do?", "expected_answer_summary": "Defines how to build an image."}'])

    exercise = generate_exercise(llm, "Docker")

    assert exercise.question == "What does a Dockerfile do?"


def test_generate_exercise_rejects_empty_concept():
    llm = ScriptedProvider([])

    with pytest.raises(ValueError):
        generate_exercise(llm, "")


def test_generate_quiz_returns_multiple_exercises():
    llm = ScriptedProvider(
        [
            '{"concept": "Docker", "question": "Q1?", "expected_answer_summary": "A1"}',
            '{"concept": "Docker", "question": "Q2?", "expected_answer_summary": "A2"}',
            '{"concept": "Docker", "question": "Q3?", "expected_answer_summary": "A3"}',
        ]
    )

    quiz = generate_quiz(llm, "Docker", num_questions=3)

    assert len(quiz) == 3
    assert quiz[0].question == "Q1?"
    assert quiz[2].question == "Q3?"


def test_generate_quiz_rejects_non_positive_count():
    llm = ScriptedProvider([])

    with pytest.raises(ValueError):
        generate_quiz(llm, "Docker", num_questions=0)
