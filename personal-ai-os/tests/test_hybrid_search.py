from datetime import datetime, timezone

from app.retrieval.document import Chunk
from app.retrieval.hybrid_search import HybridSearch, reciprocal_rank_fusion
from app.retrieval.keyword_search import KeywordSearch
from app.retrieval.vector_search import ScoredChunk, VectorStore
from tests.fakes.fake_embedding import FakeEmbeddingModel

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _chunk(id_: str, text: str) -> Chunk:
    return Chunk(
        id=id_, document_id="doc1", text=text, source="test",
        created_at=NOW, updated_at=NOW, chunk_index=0,
    )


def _scored(id_: str, text: str = "text") -> ScoredChunk:
    return ScoredChunk(chunk=_chunk(id_, text), score=0.1)


def test_rrf_favors_chunk_ranked_high_in_both_lists():
    list_a = [_scored("c1"), _scored("c2"), _scored("c3")]
    list_b = [_scored("c1"), _scored("c3"), _scored("c2")]

    fused = reciprocal_rank_fusion([list_a, list_b])

    assert fused[0].chunk.id == "c1"


def test_rrf_includes_chunk_present_in_only_one_list():
    list_a = [_scored("c1")]
    list_b = [_scored("c2")]

    fused = reciprocal_rank_fusion([list_a, list_b])
    fused_ids = {r.chunk.id for r in fused}

    assert fused_ids == {"c1", "c2"}


def test_rrf_empty_lists():
    assert reciprocal_rank_fusion([[], []]) == []


def test_hybrid_search_merges_vector_and_keyword_results():
    vector_store = VectorStore(FakeEmbeddingModel())
    keyword_search = KeywordSearch()
    chunks = [
        _chunk("c1", "RAG combines retrieval with generation."),
        _chunk("c2", "Bananas are a good source of potassium."),
    ]
    vector_store.add(chunks)
    keyword_search.add(chunks)

    hybrid = HybridSearch(vector_store, keyword_search)
    results = hybrid.search("retrieval generation RAG", top_k=2)

    assert len(results) <= 2
    assert any(r.chunk.id == "c1" for r in results)


def test_hybrid_search_empty_indices():
    hybrid = HybridSearch(VectorStore(FakeEmbeddingModel()), KeywordSearch())

    assert hybrid.search("anything") == []
