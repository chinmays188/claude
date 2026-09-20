import pytest

from app.domains.router import Domain, DomainRouter, DomainRoutingError
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_routes_to_career():
    llm = ScriptedProvider(['{"domains": ["CAREER"], "confidence": 0.9}'])
    router = DomainRouter(llm)

    result = router.route("What should I add to my resume?")

    assert result.domains == [Domain.CAREER]
    assert not result.is_cross_domain


def test_routes_to_pm():
    llm = ScriptedProvider(['{"domains": ["PM"], "confidence": 0.9}'])
    router = DomainRouter(llm)

    result = router.route("Analyze this stakeholder request.")

    assert result.domains == [Domain.PM]


def test_routes_to_finance():
    llm = ScriptedProvider(['{"domains": ["FINANCE"], "confidence": 0.9}'])
    router = DomainRouter(llm)

    result = router.route("How is my portfolio allocated?")

    assert result.domains == [Domain.FINANCE]


def test_routes_to_learning():
    llm = ScriptedProvider(['{"domains": ["LEARNING"], "confidence": 0.9}'])
    router = DomainRouter(llm)

    result = router.route("Teach me Kubernetes.")

    assert result.domains == [Domain.LEARNING]


def test_routes_to_multiple_domains():
    llm = ScriptedProvider(['{"domains": ["CAREER", "LEARNING"], "confidence": 0.85}'])
    router = DomainRouter(llm)

    result = router.route("Should I learn this technology for my career?")

    assert set(result.domains) == {Domain.CAREER, Domain.LEARNING}
    assert result.is_cross_domain


def test_low_confidence_becomes_unclear():
    llm = ScriptedProvider(['{"domains": ["CAREER"], "confidence": 0.2}'])
    router = DomainRouter(llm, confidence_threshold=0.5)

    result = router.route("something vague")

    assert result.is_unclear
    assert result.domains == []


def test_empty_domains_from_model_is_unclear():
    llm = ScriptedProvider(['{"domains": [], "confidence": 0.9}'])
    router = DomainRouter(llm)

    result = router.route("asdkjhaskjdh")

    assert result.is_unclear


def test_empty_input_raises_before_calling_llm():
    llm = ScriptedProvider([])
    router = DomainRouter(llm)

    with pytest.raises(ValueError):
        router.route("")


def test_malformed_output_raises_domain_routing_error_after_repair_exhausted():
    llm = ScriptedProvider(["not json"] * 5)
    router = DomainRouter(llm)

    with pytest.raises(DomainRoutingError):
        router.route("some request")
