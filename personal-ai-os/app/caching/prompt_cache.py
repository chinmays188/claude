from app.providers.base import LLMProvider


class PromptCacheStats:
    def __init__(self):
        self.calls = 0
        self.cache_hits = 0

    @property
    def hit_rate(self) -> float:
        return self.cache_hits / self.calls if self.calls else 0.0


class PromptCachingProvider(LLMProvider):
    """Local exact-match cache for a repeated system/context prefix. Real
    provider-side prompt caching (Gemini/Anthropic) caches at the token level on
    the server and reduces prefill cost/latency, not just avoids a full round-trip
    like this does — this wrapper demonstrates the same idea (repeated prefix,
    different suffix) and measures hit-rate locally, without depending on
    provider-specific cache APIs. Useful when the exact same prefix+suffix
    combination repeats (e.g. identical system prompt + identical user question).
    """

    def __init__(self, llm: LLMProvider):
        self._llm = llm
        self._cache: dict[str, str] = {}
        self.stats = PromptCacheStats()

    def generate(self, prompt: str) -> str:
        self.stats.calls += 1
        if prompt in self._cache:
            self.stats.cache_hits += 1
            return self._cache[prompt]

        result = self._llm.generate(prompt)
        self._cache[prompt] = result
        return result

    @property
    def model_name(self) -> str:
        return self._llm.model_name
