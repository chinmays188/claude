from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.retrieval.hybrid_search import HybridSearch
from app.retrieval.reranker import Reranker
from app.retrieval.vector_search import ScoredChunk, VectorStore


class SecureRetriever:
    """Wraps a VectorStore with permission enforcement, per Section 10:
    'The LLM must never be responsible for enforcing access control.' Filtering
    happens here, in code, before results ever leave this layer — never left to
    a prompt instruction telling the model what it may or may not use.

    Found missing while investigating "RAG & Retrieval" (disclosed gap:
    "hybrid search + reranking are real and tested but NOT actually
    wired into PersonalRagPipeline (production) yet -- SecureRetriever
    there still wraps plain vector search only"). hybrid_search/reranker
    are optional, additive (defaults to the original plain
    VectorStore.search() when neither is given, identical behavior to
    every existing caller). Order matters for permission safety:
    candidates come from hybrid_search/vector search FIRST, are
    permission-filtered SECOND, and reranked LAST -- a reranker only
    ever touches already-permitted chunks, so it can never leak
    ordering information about a chunk the requester isn't allowed to
    see in the first place."""

    def __init__(
        self,
        store: VectorStore,
        metadata_by_document_id: dict[str, PersonalDocumentMetadata],
        hybrid_search: HybridSearch | None = None,
        reranker: Reranker | None = None,
    ):
        self._store = store
        self._metadata = metadata_by_document_id
        self._hybrid_search = hybrid_search
        self._reranker = reranker

    def search(
        self,
        query: str,
        requester_id: str,
        requester_tenant_id: str,
        top_k: int = 5,
        search_k: int = 20,
    ) -> list[ScoredChunk]:
        if self._hybrid_search is not None:
            candidates = self._hybrid_search.search(query, top_k=search_k)
        else:
            candidates = self._store.search(query, top_k=search_k)

        allowed = [
            c for c in candidates
            if self._is_permitted(c, requester_id, requester_tenant_id)
        ]

        if self._reranker is not None:
            return self._reranker.rerank(query, allowed, top_k=top_k)
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
