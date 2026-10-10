from datetime import datetime, timezone

from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.knowledge.secure_retrieval import SecureRetriever
from app.multimodal.ingestion_bridge import MultimodalIngestionBridge
from app.multimodal.multimodal_orchestrator import InputKind, MultimodalConversionResult
from app.retrieval.vector_search import VectorStore
from tests.fakes.fake_embedding import FakeEmbeddingModel

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _metadata(document_id: str, owner_id: str = "alice", tenant_id: str = "t1", sensitivity: Sensitivity = Sensitivity.PERSONAL) -> PersonalDocumentMetadata:
    return PersonalDocumentMetadata(
        document_id=document_id, source="screenshot.png", title="Settings screenshot",
        created_at=NOW, updated_at=NOW, owner_id=owner_id, tenant_id=tenant_id, sensitivity=sensitivity,
    )


def _bridge():
    store = VectorStore(FakeEmbeddingModel())
    metadata: dict = {}
    bridge = MultimodalIngestionBridge(store, metadata)
    return bridge, store, metadata


def test_ingests_real_extracted_text_into_chunks():
    bridge, store, _ = _bridge()
    conversion = MultimodalConversionResult(
        kind=InputKind.IMAGE, extracted_text="The settings page shows username alice_pm with notifications disabled.",
        model_used="gemini-test",
    )

    chunks = bridge.ingest("doc1", conversion, _metadata("doc1"))

    assert len(chunks) == 1
    assert chunks[0].document_id == "doc1"
    assert "alice_pm" in chunks[0].text
    assert chunks[0].source == "image:screenshot.png"


def test_ingested_multimodal_content_is_retrievable_via_secure_retriever():
    bridge, store, metadata = _bridge()
    conversion = MultimodalConversionResult(
        kind=InputKind.IMAGE, extracted_text="The settings page shows username alice_pm with notifications disabled.",
        model_used="gemini-test",
    )
    bridge.ingest("doc1", conversion, _metadata("doc1"))

    retriever = SecureRetriever(store, metadata)
    results = retriever.search("What is the username?", requester_id="alice", requester_tenant_id="t1")

    assert len(results) == 1
    assert "alice_pm" in results[0].chunk.text
    assert results[0].chunk.source == "image:screenshot.png"


def test_permission_filtering_still_applies_to_multimodal_content():
    """The whole point of requiring PersonalDocumentMetadata for multimodal
    ingestion -- a different tenant must never retrieve another tenant's
    uploaded image/PDF content, exactly like any text document."""
    bridge, store, metadata = _bridge()
    conversion = MultimodalConversionResult(
        kind=InputKind.IMAGE, extracted_text="Confidential salary figures are shown in this screenshot.",
        model_used="gemini-test",
    )
    bridge.ingest("doc1", conversion, _metadata("doc1", owner_id="alice", tenant_id="t1"))

    retriever = SecureRetriever(store, metadata)
    results = retriever.search("salary figures", requester_id="bob", requester_tenant_id="t2")

    assert results == []


def test_empty_extracted_text_ingests_as_a_real_honest_no_op():
    bridge, _, _ = _bridge()
    conversion = MultimodalConversionResult(kind=InputKind.AUDIO, extracted_text="   ", model_used="gemini-test")

    chunks = bridge.ingest("doc1", conversion, _metadata("doc1"))

    assert chunks == []


def test_mismatched_document_id_raises():
    bridge, _, _ = _bridge()
    conversion = MultimodalConversionResult(kind=InputKind.IMAGE, extracted_text="text", model_used="gemini-test")

    import pytest

    with pytest.raises(ValueError):
        bridge.ingest("doc1", conversion, _metadata("doc2"))
