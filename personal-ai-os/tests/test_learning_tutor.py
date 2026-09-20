import pytest

from app.domains.learning.models import ContentKind
from app.domains.learning.tutor import explain_concept, generate_analogy, generate_example
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_explain_concept_tags_factual():
    llm = ScriptedProvider(['{"concept": "Docker", "content": "Docker packages an app with its dependencies.", "kind": "factual"}'])

    explanation = explain_concept(llm, "Docker")

    assert explanation.kind == ContentKind.FACTUAL
    assert "Docker" in explanation.content


def test_generate_analogy_tags_analogy():
    llm = ScriptedProvider(['{"concept": "Docker", "content": "Docker is like a shipping container for your app.", "kind": "analogy"}'])

    explanation = generate_analogy(llm, "Docker")

    assert explanation.kind == ContentKind.ANALOGY


def test_generate_example_tags_factual():
    llm = ScriptedProvider(['{"concept": "Docker", "content": "docker run hello-world", "kind": "factual"}'])

    explanation = generate_example(llm, "Docker")

    assert explanation.kind == ContentKind.FACTUAL


def test_explain_concept_rejects_empty_input():
    llm = ScriptedProvider([])

    with pytest.raises(ValueError):
        explain_concept(llm, "")


def test_generate_analogy_rejects_empty_input():
    llm = ScriptedProvider([])

    with pytest.raises(ValueError):
        generate_analogy(llm, "  ")
