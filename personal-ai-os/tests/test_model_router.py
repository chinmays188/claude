import pytest

from app.providers.base import LLMProvider
from app.routing.model_router import ModelRouter, TaskComplexity


class NamedProvider(LLMProvider):
    def __init__(self, name: str):
        self._name = name

    def generate(self, prompt: str) -> str:
        return f"response from {self._name}"

    @property
    def model_name(self) -> str:
        return self._name


def _router() -> ModelRouter:
    return ModelRouter(
        {
            TaskComplexity.SIMPLE: NamedProvider("gemini-flash-lite"),
            TaskComplexity.COMPLEX: NamedProvider("gemini-flash"),
            TaskComplexity.EVALUATION: NamedProvider("gemini-flash"),
        }
    )


def test_routes_simple_task_to_lite_model():
    router = _router()

    provider = router.route(TaskComplexity.SIMPLE)

    assert provider.model_name == "gemini-flash-lite"


def test_routes_complex_task_to_stronger_model():
    router = _router()

    provider = router.route(TaskComplexity.COMPLEX)

    assert provider.model_name == "gemini-flash"


def test_routes_evaluation_task():
    router = _router()

    provider = router.route(TaskComplexity.EVALUATION)

    assert provider.model_name == "gemini-flash"


def test_missing_provider_for_a_complexity_tier_raises():
    with pytest.raises(ValueError):
        ModelRouter({TaskComplexity.SIMPLE: NamedProvider("only-one")})
