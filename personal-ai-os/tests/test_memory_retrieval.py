from datetime import datetime, timedelta, timezone

import numpy as np

from app.memory.models import MemoryRecord, MemoryType
from app.memory.retrieval import MemoryRetriever
from app.retrieval.embeddings import EmbeddingModel

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FixedSimilarityEmbedding(EmbeddingModel):
    """Query always maps to [1, 0]; each memory's vector is set explicitly per
    test via a lookup keyed by content, so similarity is fully controlled."""

    def __init__(self, content_vectors: dict[str, list[float]]):
        self._content_vectors = content_vectors

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            if text == "__query__":
                vectors.append([1.0, 0.0])
            else:
                vectors.append(self._content_vectors.get(text, [0.0, 1.0]))
        return np.asarray(vectors, dtype="float32")

    @property
    def dimension(self) -> int:
        return 2


def _memory(id_: str, content: str, importance=0.5, updated_at=NOW, confirmed=False) -> MemoryRecord:
    return MemoryRecord(
        memory_id=id_, tenant_id="t1", user_id="u1", type=MemoryType.GOAL,
        content=content, source="test", created_at=NOW, updated_at=updated_at,
        importance=importance, user_confirmed=confirmed,
    )


def test_higher_similarity_ranks_first():
    embedding = FixedSimilarityEmbedding({"very relevant": [1.0, 0.0], "unrelated": [0.0, 1.0]})
    retriever = MemoryRetriever(embedding, weight_similarity=1.0, weight_recency=0, weight_importance=0, weight_confirmed=0)
    candidates = [_memory("m1", "unrelated"), _memory("m2", "very relevant")]

    results = retriever.rank("__query__", candidates)

    assert results[0].memory.memory_id == "m2"


def test_higher_importance_ranks_first_when_similarity_equal():
    embedding = FixedSimilarityEmbedding({"a": [1.0, 0.0], "b": [1.0, 0.0]})
    retriever = MemoryRetriever(embedding, weight_similarity=0, weight_recency=0, weight_importance=1.0, weight_confirmed=0)
    candidates = [_memory("m1", "a", importance=0.2), _memory("m2", "b", importance=0.9)]

    results = retriever.rank("__query__", candidates)

    assert results[0].memory.memory_id == "m2"


def test_more_recent_ranks_first_when_other_factors_equal():
    embedding = FixedSimilarityEmbedding({"a": [1.0, 0.0], "b": [1.0, 0.0]})
    retriever = MemoryRetriever(embedding, weight_similarity=0, weight_recency=1.0, weight_importance=0, weight_confirmed=0)
    old = NOW - timedelta(days=200)
    candidates = [_memory("m1", "a", updated_at=old), _memory("m2", "b", updated_at=NOW)]

    results = retriever.rank("__query__", candidates)

    assert results[0].memory.memory_id == "m2"


def test_confirmed_memory_ranks_first_when_other_factors_equal():
    embedding = FixedSimilarityEmbedding({"a": [1.0, 0.0], "b": [1.0, 0.0]})
    retriever = MemoryRetriever(embedding, weight_similarity=0, weight_recency=0, weight_importance=0, weight_confirmed=1.0)
    candidates = [_memory("m1", "a", confirmed=False), _memory("m2", "b", confirmed=True)]

    results = retriever.rank("__query__", candidates)

    assert results[0].memory.memory_id == "m2"


def test_top_k_limits_results():
    embedding = FixedSimilarityEmbedding({})
    retriever = MemoryRetriever(embedding)
    candidates = [_memory(f"m{i}", f"content {i}") for i in range(10)]

    results = retriever.rank("__query__", candidates, top_k=3)

    assert len(results) == 3


def test_empty_candidates_returns_empty():
    embedding = FixedSimilarityEmbedding({})
    retriever = MemoryRetriever(embedding)

    assert retriever.rank("__query__", []) == []
