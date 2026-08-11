from datetime import datetime, timezone

import pytest

from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.knowledge.secure_retrieval import SecureRetriever
from app.memory.models import MemoryRecord, MemoryType
from app.memory.retrieval import MemoryRetriever
from app.personal_rag.pipeline import PersonalRagPipeline
from app.providers.base import LLMProvider
from app.retrieval.document import Chunk
from app.retrieval.vector_search import VectorStore
from tests.fakes.fake_embedding import FakeEmbeddingModel

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _chunk(doc_id: str, text: str) -> Chunk:
    return Chunk(id=f"{doc_id}::c0", document_id=doc_id, text=text, source="test", created_at=NOW, updated_at=NOW, chunk_index=0)


def _memory(id_: str, content: str) -> MemoryRecord:
    return MemoryRecord(
        memory_id=id_, tenant_id="t1", user_id="alice", type=MemoryType.LEARNING,
        content=content, source="conversation", created_at=NOW, updated_at=NOW,
    )


def _pipeline(llm_responses: list[str], chunks: list[Chunk] = None, metadata: dict = None):
    llm = ScriptedProvider(llm_responses)
    store = VectorStore(FakeEmbeddingModel())
    store.add(chunks or [])
    secure_retriever = SecureRetriever(store, metadata or {})
    memory_retriever = MemoryRetriever(FakeEmbeddingModel())
    return PersonalRagPipeline(llm, secure_retriever, memory_retriever)


def test_answer_includes_llm_output():
    pipeline = _pipeline(["RAG is retrieval + generation."])

    result = pipeline.answer("What is RAG?", requester_id="alice", requester_tenant_id="t1", memory_candidates=[])

    assert result.answer == "RAG is retrieval + generation."


def test_answer_includes_document_citations():
    metadata = {"doc1": PersonalDocumentMetadata(
        document_id="doc1", source="notes", title="t", created_at=NOW, updated_at=NOW,
        owner_id="alice", tenant_id="t1", sensitivity=Sensitivity.PERSONAL,
    )}
    pipeline = _pipeline(["answer"], chunks=[_chunk("doc1", "RAG combines retrieval with generation.")], metadata=metadata)

    result = pipeline.answer("What is RAG?", requester_id="alice", requester_tenant_id="t1", memory_candidates=[])

    assert any(c.chunk_id == "doc1::c0" for c in result.citations)


def test_answer_uses_relevant_memory():
    pipeline = _pipeline(["answer"])
    memories = [_memory("m1", "User is learning Docker.")]

    result = pipeline.answer("What am I learning?", requester_id="alice", requester_tenant_id="t1", memory_candidates=memories)

    assert "m1" in result.memory_used


def test_documents_owned_by_others_are_never_visible_to_the_pipeline():
    metadata = {"doc1": PersonalDocumentMetadata(
        document_id="doc1", source="notes", title="t", created_at=NOW, updated_at=NOW,
        owner_id="bob", tenant_id="t1", sensitivity=Sensitivity.PERSONAL,
    )}
    pipeline = _pipeline(["answer"], chunks=[_chunk("doc1", "bob's private notes")], metadata=metadata)

    result = pipeline.answer("private notes", requester_id="alice", requester_tenant_id="t1", memory_candidates=[])

    assert result.citations == []


def test_empty_question_raises():
    pipeline = _pipeline([])

    with pytest.raises(ValueError):
        pipeline.answer("", requester_id="alice", requester_tenant_id="t1", memory_candidates=[])
