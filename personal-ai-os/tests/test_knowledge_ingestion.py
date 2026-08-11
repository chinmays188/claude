from datetime import datetime, timezone

from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.knowledge.ingestion import KnowledgeBase
from app.knowledge.parsers import default_parser_registry
from app.retrieval.vector_search import VectorStore
from tests.fakes.fake_embedding import FakeEmbeddingModel

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _metadata(doc_id: str, owner: str = "u1", tenant: str = "t1") -> PersonalDocumentMetadata:
    return PersonalDocumentMetadata(
        document_id=doc_id, source="upload", title="Test Doc",
        created_at=NOW, updated_at=NOW, owner_id=owner, tenant_id=tenant,
    )


def test_ingest_file_parses_chunks_and_stores():
    kb = KnowledgeBase(VectorStore(FakeEmbeddingModel()), default_parser_registry())

    count = kb.ingest_file("notes.txt", b"Hello world. " * 50, _metadata("doc1"), chunk_size=20)

    assert count > 0
    assert kb.metadata_by_document_id["doc1"].title == "Test Doc"


def test_ingest_document_records_metadata_by_document_id():
    from app.knowledge.document import PersonalDocument

    kb = KnowledgeBase(VectorStore(FakeEmbeddingModel()), default_parser_registry())
    doc = PersonalDocument(metadata=_metadata("doc2"), text="Some content here.")

    kb.ingest_document(doc)

    assert "doc2" in kb.metadata_by_document_id


def test_ingest_file_defaults_sensitivity_to_personal():
    kb = KnowledgeBase(VectorStore(FakeEmbeddingModel()), default_parser_registry())

    kb.ingest_file("notes.txt", b"content", _metadata("doc3"))

    assert kb.metadata_by_document_id["doc3"].sensitivity == Sensitivity.PERSONAL
