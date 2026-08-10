import logging

from app.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class AllProvidersFailedError(Exception):
    pass


class FallbackProvider(LLMProvider):
    """Tries providers in order; records which one actually served the response."""

    def __init__(self, providers: list[LLMProvider]):
        if not providers:
            raise ValueError("FallbackProvider requires at least one provider.")
        self._providers = providers
        self.last_used_provider: LLMProvider | None = None
        self.fallback_occurred: bool = False

    def generate(self, prompt: str) -> str:
        errors = []
        for index, provider in enumerate(self._providers):
            try:
                result = provider.generate(prompt)
            except Exception as exc:
                errors.append(f"{provider.model_name}: {exc}")
                continue

            self.last_used_provider = provider
            self.fallback_occurred = index > 0
            if self.fallback_occurred:
                logger.warning(
                    "Fell back to provider '%s' after failure(s): %s",
                    provider.model_name,
                    "; ".join(errors),
                )
            return result

        raise AllProvidersFailedError(
            f"All {len(self._providers)} provider(s) failed: {'; '.join(errors)}"
        )

    @property
    def model_name(self) -> str:
        if self.last_used_provider is None:
            return "unresolved"
        return self.last_used_provider.model_name
