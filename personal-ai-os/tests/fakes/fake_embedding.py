import hashlib

import numpy as np

from app.retrieval.embeddings import EmbeddingModel


class FakeEmbeddingModel(EmbeddingModel):
    """Deterministic hash-based embedding — no ML model, no network, fast and reproducible.
    Semantically meaningless, but stable: identical text -> identical vector."""

    def __init__(self, dimension: int = 16):
        self._dimension = dimension

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = [self._embed_one(text) for text in texts]
        return np.asarray(vectors, dtype="float32")

    def _embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [digest[i % len(digest)] / 255.0 for i in range(self._dimension)]

    @property
    def dimension(self) -> int:
        return self._dimension
