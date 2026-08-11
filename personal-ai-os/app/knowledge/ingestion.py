from app.knowledge.cleaner import clean_text
from app.knowledge.document import PersonalDocument, PersonalDocumentMetadata
from app.knowledge.parsers import ParserRegistry
from app.retrieval.chunking import chunk_document
from app.retrieval.document import Document
from app.retrieval.vector_search import VectorStore


class KnowledgeBase:
    """Ties together parsing, cleaning, chunking, embedding, and storage
    (Section 9's pipeline), while keeping a metadata side-table so the security
    layer (SecureRetriever) can enforce access control without ever needing the
    LLM's cooperation."""

    def __init__(self, store: VectorStore, parsers: ParserRegistry):
        self._store = store
        self._parsers = parsers
        self.metadata_by_document_id: dict[str, PersonalDocumentMetadata] = {}

    def ingest_file(
        self, filename: str, raw_bytes: bytes, metadata: PersonalDocumentMetadata,
        chunk_size: int = 200, overlap: int = 0,
    ) -> int:
        raw_text = self._parsers.parse(filename, raw_bytes)
        cleaned_text = clean_text(raw_text)
        document = PersonalDocument(metadata=metadata, text=cleaned_text)
        return self.ingest_document(document, chunk_size=chunk_size, overlap=overlap)

    def ingest_document(
        self, document: PersonalDocument, chunk_size: int = 200, overlap: int = 0
    ) -> int:
        self.metadata_by_document_id[document.metadata.document_id] = document.metadata

        rag_document = Document(
            id=document.metadata.document_id,
            text=document.text,
            source=document.metadata.source,
            created_at=document.metadata.created_at,
            updated_at=document.metadata.updated_at,
            version=document.metadata.version,
        )
        chunks = chunk_document(rag_document, chunk_size=chunk_size, overlap=overlap)
        self._store.add(chunks)
        return len(chunks)
