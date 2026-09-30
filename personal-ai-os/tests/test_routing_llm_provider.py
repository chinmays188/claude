import pytest

from app.providers.base import LLMProvider
from app.providers.fallback_provider import AllProvidersFailedError
from app.routing.model_router import (
    ModelRouter,
    RoutingLLMProvider,
    TaskComplexity,
    classify_task_complexity,
)


class NamedProvider(LLMProvider):
    def __init__(self, name: str, raises: bool = False):
        self._name = name
        self._raises = raises

    def generate(self, prompt: str) -> str:
        if self._raises:
            raise RuntimeError(f"{self._name} failed (simulated real quota exhaustion)")
        return f"response from {self._name}"

    @property
    def model_name(self) -> str:
        return self._name


def _router(strong_raises: bool = False) -> ModelRouter:
    return ModelRouter(
        {
            TaskComplexity.SIMPLE: NamedProvider("gemini-3.5-flash-lite"),
            TaskComplexity.COMPLEX: NamedProvider("gemini-3.8-flash", raises=strong_raises),
            TaskComplexity.EVALUATION: NamedProvider("gemini-3.8-flash"),
        }
    )


def test_classify_short_simple_request():
    assert classify_task_complexity("What is 2 + 2?") == TaskComplexity.SIMPLE


def test_classify_complex_via_signal_phrase():
    assert classify_task_complexity("Please compare these two options.") == TaskComplexity.COMPLEX


def test_classify_complex_via_length():
    long_text = " ".join(["word"] * 35)
    assert classify_task_complexity(long_text) == TaskComplexity.COMPLEX


def test_simple_request_routes_to_cheap_tier_no_fallback_involved():
    provider = RoutingLLMProvider(_router())

    result = provider.generate("What is 2 + 2?")

    assert result == "response from gemini-3.5-flash-lite"
    assert provider.last_decision.complexity == TaskComplexity.SIMPLE
    assert provider.last_decision.degraded is False
    assert provider.model_name == "gemini-3.5-flash-lite"


def test_complex_request_routes_to_strong_tier_when_available():
    provider = RoutingLLMProvider(_router())

    result = provider.generate("Please give me a comprehensive, detailed plan.")

    assert result == "response from gemini-3.8-flash"
    assert provider.last_decision.complexity == TaskComplexity.COMPLEX
    assert provider.last_decision.degraded is False


def test_complex_request_degrades_to_cheap_tier_on_real_strong_tier_failure():
    """Simulates the real gemini-3.8-flash daily-quota exhaustion this
    project actually hit earlier this session -- a real fallback, not a
    theoretical one."""
    provider = RoutingLLMProvider(_router(strong_raises=True))

    result = provider.generate("Please give me a comprehensive, detailed plan.")

    assert result == "response from gemini-3.5-flash-lite"
    assert provider.last_decision.complexity == TaskComplexity.COMPLEX
    assert provider.last_decision.degraded is True
    assert "quota" in provider.last_decision.reason.lower() or "degraded" in provider.last_decision.reason.lower()


def test_raises_when_every_provider_fails():
    router = ModelRouter(
        {
            TaskComplexity.SIMPLE: NamedProvider("cheap"),
            TaskComplexity.COMPLEX: NamedProvider("strong", raises=True),
            TaskComplexity.EVALUATION: NamedProvider("strong"),
        }
    )
    provider = RoutingLLMProvider(router)
    # Force both the strong and cheap tier to fail for a COMPLEX request.
    provider._cheap = NamedProvider("cheap", raises=True)
    provider._strong_with_fallback = type(provider._strong_with_fallback)(
        [NamedProvider("strong", raises=True), NamedProvider("cheap", raises=True)]
    )

    with pytest.raises(AllProvidersFailedError):
        provider.generate("Please give a comprehensive, detailed, thorough analysis.")
