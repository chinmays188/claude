from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.retrieval.vector_search import ScoredChunk, VectorStore


class SecureRetriever:
    """Wraps a VectorStore with permission enforcement, per Section 10:
    'The LLM must never be responsible for enforcing access control.' Filtering
    happens here, in code, before results ever leave this layer — never left to
    a prompt instruction telling the model what it may or may not use."""

    def __init__(self, store: VectorStore, metadata_by_document_id: dict[str, PersonalDocumentMetadata]):
        self._store = store
        self._metadata = metadata_by_document_id

    def search(
        self,
        query: str,
        requester_id: str,
        requester_tenant_id: str,
        top_k: int = 5,
        search_k: int = 20,
    ) -> list[ScoredChunk]:
        candidates = self._store.search(query, top_k=search_k)
        allowed = [
            c for c in candidates
            if self._is_permitted(c, requester_id, requester_tenant_id)
        ]
        return allowed[:top_k]

    def _is_permitted(self, scored: ScoredChunk, requester_id: str, requester_tenant_id: str) -> bool:
        metadata = self._metadata.get(scored.chunk.document_id)
        if metadata is None:
            return False  # no metadata -> cannot verify ownership -> deny by default

        if metadata.tenant_id != requester_tenant_id:
            return False

        if metadata.sensitivity == Sensitivity.PUBLIC:
            return True

        if metadata.owner_id == requester_id:
            return True

        return requester_id in metadata.permissions
