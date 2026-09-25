import pytest

from app.domains.router import Domain
from app.providers.base import LLMProvider
from app.routing.classifier import TaskType
from app.routing.unified_router import UnifiedRouter, UnifiedRoutingError


class ScriptedProvider(LLMProvider):
    """Responses consumed in order: DomainRouter's call first, then
    TaskClassifier's call (matches UnifiedRouter.route()'s real call order)."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_classifies_both_domain_and_task_type():
    llm = ScriptedProvider(
        [
            '{"domains": ["CAREER"], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.85}',
        ]
    )
    router = UnifiedRouter(llm)

    result = router.route("Should I learn Kubernetes for my career?")

    assert result.domain == Domain.CAREER
    assert result.domain_confidence == 0.9
    assert result.task_type == TaskType.RESEARCH
    assert result.task_confidence == 0.85


def test_domain_none_means_general_not_an_error():
    llm = ScriptedProvider(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.8}',
        ]
    )
    router = UnifiedRouter(llm)

    result = router.route("What's 47 times 12?")

    assert result.domain is None  # GENERAL, not an error
    assert result.task_type == TaskType.RESEARCH  # task-type still classified independently


def test_cross_domain_surfaces_primary_and_all_domains():
    llm = ScriptedProvider(
        [
            '{"domains": ["CAREER", "LEARNING"], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.8}',
        ]
    )
    router = UnifiedRouter(llm)

    result = router.route("Should I learn Kubernetes for my career?")

    assert result.domain == Domain.CAREER  # first one, as the primary
    assert result.all_domains == [Domain.CAREER, Domain.LEARNING]
    assert result.is_cross_domain is True


def test_task_type_unclear_is_still_returned_not_raised():
    llm = ScriptedProvider(
        [
            '{"domains": ["FINANCE"], "confidence": 0.9}',
            '{"task_type": "unclear", "confidence": 0.2}',
        ]
    )
    router = UnifiedRouter(llm)

    result = router.route("hmm")

    assert result.domain == Domain.FINANCE
    assert result.task_type == TaskType.UNCLEAR


def test_empty_input_raises_before_any_classification():
    llm = ScriptedProvider([])
    router = UnifiedRouter(llm)

    with pytest.raises(ValueError):
        router.route("")
