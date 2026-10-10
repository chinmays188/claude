"""Closes the one real gap "Multimodal AI" has disclosed across every
prior learning-goal update: extraction/understanding is real (text,
image, PDF, audio all correctly turn into text via
MultimodalOrchestrator), but that extracted text never became part of
this project's actual knowledge base -- it was answered once, in the
same request, then discarded. There was no way to ask a later question
and have it surface a previously-uploaded image/PDF/audio's content.

MultimodalIngestionBridge closes it with pure composition, not new
infrastructure: it takes a real MultimodalConversionResult (already
produced by MultimodalOrchestrator.handle()) plus the same
PersonalDocumentMetadata fields every text document already requires
(owner/tenant/sensitivity -- Section 10's access-control rule applies
identically to multimodal content, no special-casing), builds a real
Document, and runs it through the exact same, UNCHANGED
chunk_document()/VectorStore.add() every text document uses. The
resulting chunks are retrievable through SecureRetriever exactly like
any other document -- same permission filtering, same hybrid
search/reranking, same citation shape -- the only difference is the
`source` string, tagged with the media kind (e.g. "image:screenshot.png")
so a citation makes clear the content came from an uploaded file, not a
typed note.
"""

from datetime import datetime, timezone

from app.knowledge.document import PersonalDocumentMetadata
from app.multimodal.multimodal_orchestrator import MultimodalConversionResult
from app.retrieval.chunking import chunk_document
from app.retrieval.document import Chunk, Document
from app.retrieval.vector_search import VectorStore


class MultimodalIngestionBridge:
    def __init__(self, store: VectorStore, metadata_by_document_id: dict[str, PersonalDocumentMetadata]):
        self._store = store
        self._metadata = metadata_by_document_id

    def ingest(
        self, document_id: str, conversion: MultimodalConversionResult,
        metadata: PersonalDocumentMetadata, chunk_size: int = 200, overlap: int = 0,
    ) -> list[Chunk]:
        """Indexes one already-extracted multimodal result for later
        retrieval. Returns the real chunks that were added (empty list for
        empty/whitespace-only extracted text -- a real, honest no-op, not
        an error, matching ingest()'s own behavior for an empty document)."""
        if metadata.document_id != document_id:
            raise ValueError(
                f"metadata.document_id ({metadata.document_id!r}) must match document_id ({document_id!r})."
            )

        now = datetime.now(timezone.utc)
        document = Document(
            id=document_id, text=conversion.extracted_text,
            source=f"{conversion.kind.value}:{metadata.source}",
            created_at=now, updated_at=now,
        )

        chunks = chunk_document(document, chunk_size=chunk_size, overlap=overlap)
        self._store.add(chunks)
        self._metadata[document_id] = metadata
        return chunks
