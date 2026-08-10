from app.caching.semantic_cache import SemanticCache, SemanticCachingProvider, looks_time_sensitive
from app.providers.base import LLMProvider
from tests.fakes.fake_semantic_embedding import FakeSemanticEmbedding


class CountingProvider(LLMProvider):
    def __init__(self):
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return f"response #{self.calls}"

    @property
    def model_name(self) -> str:
        return "counting-model"


def test_semantically_similar_query_hits_cache():
    cache = SemanticCache(FakeSemanticEmbedding(), similarity_threshold=0.9)
    cache.put("What is RAG?", "RAG combines retrieval with generation.")

    result = cache.get("Can you explain retrieval augmented generation?")

    assert result == "RAG combines retrieval with generation."


def test_unrelated_query_misses_cache():
    cache = SemanticCache(FakeSemanticEmbedding(), similarity_threshold=0.9)
    cache.put("What is RAG?", "RAG combines retrieval with generation.")

    result = cache.get("What's the weather like today")

    assert result is None


def test_time_sensitive_query_never_cached():
    cache = SemanticCache(FakeSemanticEmbedding(), similarity_threshold=0.5)

    cache.put("What is RAG today?", "some answer")

    assert len(cache) == 0


def test_time_sensitive_query_never_reads_from_cache_even_if_similar():
    cache = SemanticCache(FakeSemanticEmbedding(), similarity_threshold=0.5)
    cache.put("What is RAG?", "cached answer")

    result = cache.get("What is RAG today?")

    assert result is None


def test_looks_time_sensitive_detects_marker_words():
    assert looks_time_sensitive("What changed in RAG recently?")
    assert looks_time_sensitive("What is the latest news?")
    assert not looks_time_sensitive("Explain RAG.")


def test_semantic_caching_provider_avoids_duplicate_llm_call():
    inner = CountingProvider()
    cache = SemanticCache(FakeSemanticEmbedding(), similarity_threshold=0.9)
    provider = SemanticCachingProvider(inner, cache)

    provider.generate("What is RAG?")
    provider.generate("Can you explain retrieval augmented generation?")

    assert inner.calls == 1


def test_semantic_caching_provider_always_calls_llm_for_time_sensitive_queries():
    inner = CountingProvider()
    cache = SemanticCache(FakeSemanticEmbedding(), similarity_threshold=0.5)
    provider = SemanticCachingProvider(inner, cache)

    provider.generate("What is RAG today?")
    provider.generate("What is RAG today?")

    assert inner.calls == 2
