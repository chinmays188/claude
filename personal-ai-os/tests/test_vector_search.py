from datetime import datetime, timezone

from app.retrieval.document import Chunk
from app.retrieval.vector_search import VectorStore
from tests.fakes.fake_embedding import FakeEmbeddingModel

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _chunk(id_: str, text: str) -> Chunk:
    return Chunk(
        id=id_, document_id="doc1", text=text, source="test",
        created_at=NOW, updated_at=NOW, chunk_index=0,
    )


def test_empty_store_returns_no_results():
    store = VectorStore(FakeEmbeddingModel())

    results = store.search("anything")

    assert results == []


def test_exact_text_match_ranks_first():
    store = VectorStore(FakeEmbeddingModel())
    store.add(
        [
            _chunk("c1", "The Eiffel Tower is in Paris."),
            _chunk("c2", "Bananas are a good source of potassium."),
        ]
    )

    results = store.search("The Eiffel Tower is in Paris.", top_k=2)

    assert results[0].chunk.id == "c1"


def test_top_k_limits_results():
    store = VectorStore(FakeEmbeddingModel())
    store.add([_chunk(f"c{i}", f"document number {i}") for i in range(5)])

    results = store.search("document number 3", top_k=2)

    assert len(results) == 2


def test_len_reflects_chunk_count():
    store = VectorStore(FakeEmbeddingModel())
    store.add([_chunk("c1", "hello"), _chunk("c2", "world")])

    assert len(store) == 2
