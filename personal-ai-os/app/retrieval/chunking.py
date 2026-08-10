from app.retrieval.document import Chunk, Document


def chunk_document(document: Document, chunk_size: int = 200, overlap: int = 0) -> list[Chunk]:
    """Chunk by whitespace-separated words. chunk_size/overlap are word counts,
    a simple proxy for tokens — good enough for local experimentation."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size.")

    words = document.text.split()
    if not words:
        return []

    step = chunk_size - overlap
    chunks = []
    for index, start in enumerate(range(0, len(words), step)):
        piece = words[start : start + chunk_size]
        if not piece:
            break
        chunks.append(
            Chunk(
                id=f"{document.id}::chunk{index}",
                document_id=document.id,
                text=" ".join(piece),
                source=document.source,
                created_at=document.created_at,
                updated_at=document.updated_at,
                chunk_index=index,
            )
        )
        if start + chunk_size >= len(words):
            break

    return chunks
