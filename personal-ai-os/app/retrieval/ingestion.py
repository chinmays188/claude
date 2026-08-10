from app.retrieval.chunking import chunk_document
from app.retrieval.document import Document
from app.retrieval.vector_search import VectorStore


def ingest(documents: list[Document], store: VectorStore, chunk_size: int = 200, overlap: int = 0) -> int:
    """Chunk and embed each document into the vector store. Returns total chunks added."""
    total = 0
    for document in documents:
        chunks = chunk_document(document, chunk_size=chunk_size, overlap=overlap)
        store.add(chunks)
        total += len(chunks)
    return total
