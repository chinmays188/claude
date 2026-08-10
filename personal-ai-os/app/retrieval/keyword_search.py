from rank_bm25 import BM25Okapi

from app.retrieval.document import Chunk
from app.retrieval.vector_search import ScoredChunk


class KeywordSearch:
    """BM25 lexical search over ingested chunks."""

    def __init__(self):
        self._chunks: list[Chunk] = []
        self._bm25: BM25Okapi | None = None

    def add(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        self._chunks.extend(chunks)
        self._bm25 = BM25Okapi([c.text.lower().split() for c in self._chunks])

    def search(self, query: str, top_k: int = 5) -> list[ScoredChunk]:
        if not self._chunks or self._bm25 is None:
            return []
        scores = self._bm25.get_scores(query.lower().split())
        ranked = sorted(
            zip(self._chunks, scores), key=lambda pair: pair[1], reverse=True
        )
        return [ScoredChunk(chunk=c, score=float(s)) for c, s in ranked[:top_k] if s > 0]

    def __len__(self) -> int:
        return len(self._chunks)
