from datetime import datetime, timezone

from app.retrieval.document import Chunk
from app.retrieval.vector_search import VectorStore
from app.tools.retrieval_tool import RetrievalTool
from tests.fakes.fake_embedding import FakeEmbeddingModel

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _chunk(id_: str, text: str) -> Chunk:
    return Chunk(
        id=id_, document_id="doc1", text=text, source="test",
        created_at=NOW, updated_at=NOW, chunk_index=0,
    )


def test_retrieval_tool_returns_relevant_chunk_with_citation():
    store = VectorStore(FakeEmbeddingModel())
    store.add([_chunk("c1", "RAG combines retrieval with generation.")])
    tool = RetrievalTool(store)

    result = tool.call({"query": "RAG combines retrieval with generation."})

    assert "c1" in result
    assert "RAG combines retrieval with generation." in result


def test_retrieval_tool_empty_store_returns_no_results_message():
    store = VectorStore(FakeEmbeddingModel())
    tool = RetrievalTool(store)

    result = tool.call({"query": "anything"})

    assert "No relevant documents found." == result


def test_retrieval_tool_default_top_k():
    store = VectorStore(FakeEmbeddingModel())
    store.add([_chunk(f"c{i}", f"chunk number {i}") for i in range(10)])
    tool = RetrievalTool(store)

    result = tool.call({"query": "chunk number 5"})

    assert result.count("[c") == 3
