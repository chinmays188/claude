from app.providers.base import LLMProvider


class FakeProvider(LLMProvider):
    """Deterministic stand-in for tests — no network calls."""

    def __init__(self, canned_response: str = "fake response"):
        self._canned_response = canned_response

    def generate(self, prompt: str) -> str:
        return self._canned_response

    @property
    def model_name(self) -> str:
        return "fake-model"
