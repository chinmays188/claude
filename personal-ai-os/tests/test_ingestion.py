from datetime import datetime, timezone

from app.retrieval.document import Document
from app.retrieval.ingestion import ingest
from app.retrieval.vector_search import VectorStore
from tests.fakes.fake_embedding import FakeEmbeddingModel

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_ingest_chunks_and_stores_all_documents():
    docs = [
        Document(id="d1", text=" ".join(f"w{i}" for i in range(15)), source="a", created_at=NOW, updated_at=NOW),
        Document(id="d2", text=" ".join(f"w{i}" for i in range(5)), source="b", created_at=NOW, updated_at=NOW),
    ]
    store = VectorStore(FakeEmbeddingModel())

    total = ingest(docs, store, chunk_size=10, overlap=0)

    assert total == 3  # d1 -> 2 chunks, d2 -> 1 chunk
    assert len(store) == 3


def test_ingest_empty_document_list():
    store = VectorStore(FakeEmbeddingModel())

    total = ingest([], store)

    assert total == 0
    assert len(store) == 0
