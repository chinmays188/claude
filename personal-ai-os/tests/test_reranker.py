from datetime import datetime, timezone

from app.retrieval.document import Chunk
from app.retrieval.vector_search import ScoredChunk
from tests.fakes.fake_reranker import FakeReranker

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _scored(id_: str) -> ScoredChunk:
    chunk = Chunk(
        id=id_, document_id="doc1", text="text", source="test",
        created_at=NOW, updated_at=NOW, chunk_index=0,
    )
    return ScoredChunk(chunk=chunk, score=0.1)


def test_reranker_changes_order():
    reranker = FakeReranker()
    candidates = [_scored("c1"), _scored("c2"), _scored("c3")]

    reranked = reranker.rerank("query", candidates, top_k=3)

    assert [r.chunk.id for r in reranked] == ["c3", "c2", "c1"]


def test_reranker_respects_top_k():
    reranker = FakeReranker()
    candidates = [_scored("c1"), _scored("c2"), _scored("c3")]

    reranked = reranker.rerank("query", candidates, top_k=1)

    assert len(reranked) == 1


def test_reranker_empty_candidates():
    reranker = FakeReranker()

    assert reranker.rerank("query", [], top_k=5) == []
