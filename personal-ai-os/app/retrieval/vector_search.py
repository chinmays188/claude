import numpy as np

from app.retrieval.document import Chunk
from app.retrieval.embeddings import EmbeddingModel


class ScoredChunk:
    def __init__(self, chunk: Chunk, score: float):
        self.chunk = chunk
        self.score = score


class VectorStore:
    """FAISS-backed flat L2 index. Fine for local/small-scale experimentation;
    not intended to scale beyond a few thousand chunks."""

    def __init__(self, embedding_model: EmbeddingModel):
        import faiss

        self._embedding_model = embedding_model
        self._index = faiss.IndexFlatL2(embedding_model.dimension)
        self._chunks: list[Chunk] = []

    def add(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        vectors = self._embedding_model.embed([c.text for c in chunks])
        self._index.add(vectors)
        self._chunks.extend(chunks)

    def search(self, query: str, top_k: int = 5) -> list[ScoredChunk]:
        if not self._chunks:
            return []
        query_vector = self._embedding_model.embed([query])
        distances, indices = self._index.search(query_vector, min(top_k, len(self._chunks)))
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            results.append(ScoredChunk(chunk=self._chunks[idx], score=float(distance)))
        return results

    def __len__(self) -> int:
        return len(self._chunks)
