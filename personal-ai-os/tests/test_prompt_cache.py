from app.caching.prompt_cache import PromptCachingProvider
from app.providers.base import LLMProvider


class CountingProvider(LLMProvider):
    def __init__(self):
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return f"response #{self.calls}"

    @property
    def model_name(self) -> str:
        return "counting-model"


def test_identical_prompt_hits_cache_on_second_call():
    inner = CountingProvider()
    cached = PromptCachingProvider(inner)

    first = cached.generate("Explain RAG.")
    second = cached.generate("Explain RAG.")

    assert first == second
    assert inner.calls == 1  # underlying LLM only called once
    assert cached.stats.hit_rate == 0.5


def test_different_prompts_both_call_underlying_llm():
    inner = CountingProvider()
    cached = PromptCachingProvider(inner)

    cached.generate("Explain RAG.")
    cached.generate("Explain fine-tuning.")

    assert inner.calls == 2
    assert cached.stats.hit_rate == 0.0


def test_model_name_passes_through():
    inner = CountingProvider()
    cached = PromptCachingProvider(inner)

    assert cached.model_name == "counting-model"
