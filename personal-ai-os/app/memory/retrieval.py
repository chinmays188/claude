from datetime import datetime, timezone

from app.memory.models import MemoryRecord
from app.retrieval.embeddings import EmbeddingModel


class RankedMemory:
    def __init__(self, memory: MemoryRecord, score: float):
        self.memory = memory
        self.score = score


class MemoryRetriever:
    """Ranks candidate memories per Section 13: semantic similarity, recency,
    importance, and explicit user confirmation, combined into one relevance
    score. Task-relevance filtering (the 5th factor) is left to the caller,
    since 'current task' is context this module doesn't own."""

    def __init__(
        self,
        embedding_model: EmbeddingModel,
        weight_similarity: float = 0.4,
        weight_recency: float = 0.2,
        weight_importance: float = 0.3,
        weight_confirmed: float = 0.1,
        recency_half_life_days: float = 30.0,
    ):
        self._embedding_model = embedding_model
        self._w_similarity = weight_similarity
        self._w_recency = weight_recency
        self._w_importance = weight_importance
        self._w_confirmed = weight_confirmed
        self._half_life_days = recency_half_life_days

    def rank(self, query: str, candidates: list[MemoryRecord], top_k: int = 5) -> list[RankedMemory]:
        if not candidates:
            return []

        query_vec = self._embedding_model.embed([query])[0]
        content_vecs = self._embedding_model.embed([m.content for m in candidates])

        now = datetime.now(timezone.utc)
        scored = []
        for memory, content_vec in zip(candidates, content_vecs):
            similarity = _cosine_similarity(query_vec, content_vec)
            recency = self._recency_score(memory.updated_at, now)
            confirmed = 1.0 if memory.user_confirmed else 0.0

            score = (
                self._w_similarity * similarity
                + self._w_recency * recency
                + self._w_importance * memory.importance
                + self._w_confirmed * confirmed
            )
            scored.append(RankedMemory(memory=memory, score=score))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    def _recency_score(self, updated_at: datetime, now: datetime) -> float:
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        age_days = max((now - updated_at).total_seconds() / 86400, 0)
        return 0.5 ** (age_days / self._half_life_days)


def _cosine_similarity(a, b) -> float:
    import numpy as np

    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)
