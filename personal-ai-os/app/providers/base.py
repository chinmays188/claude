from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return raw text completion for the given prompt."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier of the underlying model, for logging/attribution."""
