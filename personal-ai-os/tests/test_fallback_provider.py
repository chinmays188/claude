import pytest

from app.providers.base import LLMProvider
from app.providers.fallback_provider import AllProvidersFailedError, FallbackProvider


class StaticProvider(LLMProvider):
    def __init__(self, name: str, response: str | None = None, fails: bool = False):
        self._name = name
        self._response = response
        self._fails = fails

    def generate(self, prompt: str) -> str:
        if self._fails:
            raise RuntimeError(f"{self._name} unavailable")
        return self._response

    @property
    def model_name(self) -> str:
        return self._name


def test_primary_success_no_fallback():
    primary = StaticProvider("primary", response="ok")
    secondary = StaticProvider("secondary", response="should not be used")
    chain = FallbackProvider([primary, secondary])

    result = chain.generate("hello")

    assert result == "ok"
    assert chain.fallback_occurred is False
    assert chain.model_name == "primary"


def test_primary_fails_secondary_succeeds():
    primary = StaticProvider("primary", fails=True)
    secondary = StaticProvider("secondary", response="fallback answer")
    chain = FallbackProvider([primary, secondary])

    result = chain.generate("hello")

    assert result == "fallback answer"
    assert chain.fallback_occurred is True
    assert chain.model_name == "secondary"


def test_all_providers_fail_raises():
    primary = StaticProvider("primary", fails=True)
    secondary = StaticProvider("secondary", fails=True)
    chain = FallbackProvider([primary, secondary])

    with pytest.raises(AllProvidersFailedError):
        chain.generate("hello")


def test_requires_at_least_one_provider():
    with pytest.raises(ValueError):
        FallbackProvider([])
