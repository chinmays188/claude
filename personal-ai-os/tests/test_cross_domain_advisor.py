import pytest

from app.domains.cross_domain.advisor import DomainPerspective, combine_domain_perspectives
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_combines_perspectives_into_kubernetes_example():
    # Section 31's exact worked example.
    llm = ScriptedProvider(
        ['{"career_relevance": "HIGH", "current_work_relevance": "MEDIUM", "learning_difficulty": "HIGH", '
         '"recommended_priority": "MEDIUM", "reasoning": "Kubernetes is highly valued for target AI PM roles, '
         'moderately relevant to current post-sales work, but difficult to learn quickly."}']
    )
    perspectives = [
        DomainPerspective(domain="LEARNING", perspective="Kubernetes is a container orchestration platform, considered advanced to learn."),
        DomainPerspective(domain="CAREER", perspective="Kubernetes appears frequently in target AI PM job descriptions."),
        DomainPerspective(domain="PM", perspective="Current post-sales work touches deployment occasionally but not deeply."),
    ]

    recommendation = combine_domain_perspectives(llm, "Should I learn Kubernetes?", perspectives)

    assert recommendation.career_relevance == "HIGH"
    assert recommendation.recommended_priority == "MEDIUM"


def test_rejects_empty_question():
    llm = ScriptedProvider([])

    with pytest.raises(ValueError):
        combine_domain_perspectives(llm, "", [DomainPerspective(domain="LEARNING", perspective="x")])


def test_rejects_empty_perspectives_list():
    llm = ScriptedProvider([])

    with pytest.raises(ValueError):
        combine_domain_perspectives(llm, "Should I learn X?", [])
