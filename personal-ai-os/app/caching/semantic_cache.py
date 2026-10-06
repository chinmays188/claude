import re

import numpy as np

from app.providers.base import LLMProvider
from app.retrieval.embeddings import EmbeddingModel

FRESHNESS_MARKERS = re.compile(
    r"\b(today|now|currently|latest|recent(ly)?|this week|this month|changed|update[ds]?)\b",
    re.IGNORECASE,
)


def looks_time_sensitive(query: str) -> bool:
    """Section 41: never semantically cache live/rapidly-changing/explicitly
    latest-data requests. A simple marker-word heuristic — not exhaustive, but a
    clear, auditable rule rather than leaving staleness detection implicit."""
    return bool(FRESHNESS_MARKERS.search(query))


class SemanticCache:
    def __init__(self, embedding_model: EmbeddingModel, similarity_threshold: float = 0.92):
        self._embedding_model = embedding_model
        self._threshold = similarity_threshold
        self._entries: list[tuple[np.ndarray, str, str]] = []  # (vector, query, response)

    def get(self, query: str) -> str | None:
        if looks_time_sensitive(query) or not self._entries:
            return None

        query_vec = self._embedding_model.embed([query])[0]
        best_score = -1.0
        best_response = None
        for vec, _, response in self._entries:
            score = _cosine_similarity(query_vec, vec)
            if score > best_score:
                best_score = score
                best_response = response

        if best_score >= self._threshold:
            return best_response
        return None

    def put(self, query: str, response: str) -> None:
        if looks_time_sensitive(query):
            return
        vec = self._embedding_model.embed([query])[0]
        self._entries.append((vec, query, response))

    def __len__(self) -> int:
        return len(self._entries)


class SemanticCacheStats:
    """Real hit/miss counters -- found missing while investigating 'AI Cost &
    Latency Engineering': PromptCachingProvider already tracked this
    (PromptCacheStats), SemanticCachingProvider never did, so there was no
    way to show a real hit rate for the semantic cache anywhere."""

    def __init__(self):
        self.calls = 0
        self.cache_hits = 0

    @property
    def hit_rate(self) -> float:
        return self.cache_hits / self.calls if self.calls else 0.0


class SemanticCachingProvider(LLMProvider):
    def __init__(self, llm: LLMProvider, cache: SemanticCache):
        self._llm = llm
        self._cache = cache
        self.stats = SemanticCacheStats()

    def generate(self, prompt: str) -> str:
        self.stats.calls += 1
        cached = self._cache.get(prompt)
        if cached is not None:
            self.stats.cache_hits += 1
            return cached

        result = self._llm.generate(prompt)
        self._cache.put(prompt, result)
        return result

    @property
    def model_name(self) -> str:
        return self._llm.model_name


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)
