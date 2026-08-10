from app.retrieval.reranker import Reranker
from app.retrieval.vector_search import ScoredChunk


class FakeReranker(Reranker):
    """Reverses candidate order — deterministic, makes reordering effects visible in tests."""

    def rerank(self, query: str, candidates: list[ScoredChunk], top_k: int = 5) -> list[ScoredChunk]:
        return list(reversed(candidates))[:top_k]
