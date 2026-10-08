from datetime import datetime, timezone

from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.knowledge.secure_retrieval import SecureRetriever
from app.retrieval.document import Chunk
from app.retrieval.hybrid_search import HybridSearch
from app.retrieval.keyword_search import KeywordSearch
from app.retrieval.reranker import Reranker
from app.retrieval.vector_search import ScoredChunk, VectorStore
from tests.fakes.fake_embedding import FakeEmbeddingModel

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _chunk(doc_id: str, text: str) -> Chunk:
    return Chunk(
        id=f"{doc_id}::c0", document_id=doc_id, text=text, source="test",
        created_at=NOW, updated_at=NOW, chunk_index=0,
    )


def _metadata(doc_id: str, owner: str, tenant: str, sensitivity: Sensitivity, permissions: list[str] = None) -> PersonalDocumentMetadata:
    return PersonalDocumentMetadata(
        document_id=doc_id, source="test", title="t", created_at=NOW, updated_at=NOW,
        owner_id=owner, tenant_id=tenant, sensitivity=sensitivity, permissions=permissions or [],
    )


def _store_with(chunks: list[Chunk]) -> VectorStore:
    store = VectorStore(FakeEmbeddingModel())
    store.add(chunks)
    return store


def test_owner_can_read_own_personal_document():
    store = _store_with([_chunk("doc1", "my private notes")])
    metadata = {"doc1": _metadata("doc1", owner="alice", tenant="t1", sensitivity=Sensitivity.PERSONAL)}
    retriever = SecureRetriever(store, metadata)

    results = retriever.search("my private notes", requester_id="alice", requester_tenant_id="t1")

    assert len(results) == 1


def test_non_owner_cannot_read_personal_document():
    store = _store_with([_chunk("doc1", "my private notes")])
    metadata = {"doc1": _metadata("doc1", owner="alice", tenant="t1", sensitivity=Sensitivity.PERSONAL)}
    retriever = SecureRetriever(store, metadata)

    results = retriever.search("my private notes", requester_id="bob", requester_tenant_id="t1")

    assert results == []


def test_public_document_readable_by_anyone_in_same_tenant():
    store = _store_with([_chunk("doc1", "public info")])
    metadata = {"doc1": _metadata("doc1", owner="alice", tenant="t1", sensitivity=Sensitivity.PUBLIC)}
    retriever = SecureRetriever(store, metadata)

    results = retriever.search("public info", requester_id="bob", requester_tenant_id="t1")

    assert len(results) == 1


def test_cross_tenant_access_denied_even_for_public_document():
    store = _store_with([_chunk("doc1", "public info")])
    metadata = {"doc1": _metadata("doc1", owner="alice", tenant="tenantA", sensitivity=Sensitivity.PUBLIC)}
    retriever = SecureRetriever(store, metadata)

    results = retriever.search("public info", requester_id="bob", requester_tenant_id="tenantB")

    assert results == []


def test_explicit_permission_grants_access_to_confidential_document():
    store = _store_with([_chunk("doc1", "confidential info")])
    metadata = {
        "doc1": _metadata(
            "doc1", owner="alice", tenant="t1",
            sensitivity=Sensitivity.CONFIDENTIAL, permissions=["bob"],
        )
    }
    retriever = SecureRetriever(store, metadata)

    results = retriever.search("confidential info", requester_id="bob", requester_tenant_id="t1")

    assert len(results) == 1


def test_no_permission_denies_access_to_confidential_document():
    store = _store_with([_chunk("doc1", "confidential info")])
    metadata = {"doc1": _metadata("doc1", owner="alice", tenant="t1", sensitivity=Sensitivity.CONFIDENTIAL)}
    retriever = SecureRetriever(store, metadata)

    results = retriever.search("confidential info", requester_id="carol", requester_tenant_id="t1")

    assert results == []


def test_chunk_with_no_metadata_denied_by_default():
    store = _store_with([_chunk("unknown_doc", "mystery content")])
    retriever = SecureRetriever(store, metadata_by_document_id={})

    results = retriever.search("mystery content", requester_id="alice", requester_tenant_id="t1")

    assert results == []


def test_mixed_results_filtered_to_only_permitted_chunks():
    store = _store_with(
        [
            _chunk("doc_alice", "alice's private content"),
            _chunk("doc_bob", "bob's private content"),
        ]
    )
    metadata = {
        "doc_alice": _metadata("doc_alice", owner="alice", tenant="t1", sensitivity=Sensitivity.PERSONAL),
        "doc_bob": _metadata("doc_bob", owner="bob", tenant="t1", sensitivity=Sensitivity.PERSONAL),
    }
    retriever = SecureRetriever(store, metadata)

    results = retriever.search("private content", requester_id="alice", requester_tenant_id="t1", search_k=10)

    assert all(r.chunk.document_id == "doc_alice" for r in results)


class _RecordingReranker(Reranker):
    """Records exactly which chunks it was actually asked to rerank --
    used to prove a denied chunk never reaches the reranker at all."""

    def __init__(self):
        self.seen_document_ids: list[str] = []

    def rerank(self, query: str, candidates: list[ScoredChunk], top_k: int = 5) -> list[ScoredChunk]:
        self.seen_document_ids = [c.chunk.document_id for c in candidates]
        return candidates[:top_k]


def test_hybrid_search_is_used_when_given():
    chunks = [_chunk("doc1", "my private notes about kubernetes")]
    store = _store_with(chunks)
    keyword_search = KeywordSearch()
    keyword_search.add(chunks)
    hybrid = HybridSearch(store, keyword_search)
    metadata = {"doc1": _metadata("doc1", owner="alice", tenant="t1", sensitivity=Sensitivity.PERSONAL)}
    retriever = SecureRetriever(store, metadata, hybrid_search=hybrid)

    results = retriever.search("kubernetes", requester_id="alice", requester_tenant_id="t1")

    assert len(results) == 1


def test_reranker_only_ever_sees_already_permitted_chunks():
    """Real permission-safety guarantee: a reranker must never be handed
    a chunk the requester isn't allowed to see, even if that chunk
    scored highly in the underlying search -- reranking happens AFTER
    permission filtering, never before."""
    store = _store_with(
        [
            _chunk("doc_alice", "alice's private content"),
            _chunk("doc_bob", "bob's private content"),
        ]
    )
    metadata = {
        "doc_alice": _metadata("doc_alice", owner="alice", tenant="t1", sensitivity=Sensitivity.PERSONAL),
        "doc_bob": _metadata("doc_bob", owner="bob", tenant="t1", sensitivity=Sensitivity.PERSONAL),
    }
    reranker = _RecordingReranker()
    retriever = SecureRetriever(store, metadata, reranker=reranker)

    retriever.search("private content", requester_id="alice", requester_tenant_id="t1", search_k=10)

    assert reranker.seen_document_ids == ["doc_alice"]  # doc_bob never reached the reranker


def test_reranker_result_is_returned():
    store = _store_with([_chunk("doc1", "my private notes")])
    metadata = {"doc1": _metadata("doc1", owner="alice", tenant="t1", sensitivity=Sensitivity.PERSONAL)}
    reranker = _RecordingReranker()
    retriever = SecureRetriever(store, metadata, reranker=reranker)

    results = retriever.search("my private notes", requester_id="alice", requester_tenant_id="t1")

    assert len(results) == 1
    assert reranker.seen_document_ids == ["doc1"]
