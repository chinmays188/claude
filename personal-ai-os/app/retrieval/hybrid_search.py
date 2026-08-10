from app.retrieval.keyword_search import KeywordSearch
from app.retrieval.vector_search import ScoredChunk, VectorStore


def reciprocal_rank_fusion(
    result_lists: list[list[ScoredChunk]], k: int = 60
) -> list[ScoredChunk]:
    """Merge multiple ranked result lists by reciprocal rank, avoiding the need
    to normalize incompatible score scales (L2 distance vs. BM25 score)."""
    fused_scores: dict[str, float] = {}
    chunk_by_id = {}

    for results in result_lists:
        for rank, scored in enumerate(results):
            chunk_by_id[scored.chunk.id] = scored.chunk
            fused_scores[scored.chunk.id] = fused_scores.get(scored.chunk.id, 0.0) + 1.0 / (
                k + rank + 1
            )

    ranked_ids = sorted(fused_scores, key=lambda cid: fused_scores[cid], reverse=True)
    return [ScoredChunk(chunk=chunk_by_id[cid], score=fused_scores[cid]) for cid in ranked_ids]


class HybridSearch:
    def __init__(self, vector_store: VectorStore, keyword_search: KeywordSearch):
        self._vector_store = vector_store
        self._keyword_search = keyword_search

    def search(self, query: str, top_k: int = 5, candidate_k: int = 20) -> list[ScoredChunk]:
        vector_results = self._vector_store.search(query, top_k=candidate_k)
        keyword_results = self._keyword_search.search(query, top_k=candidate_k)
        fused = reciprocal_rank_fusion([vector_results, keyword_results])
        return fused[:top_k]
