import numpy as np

from app.retrieval.embeddings import EmbeddingModel


class FakeSemanticEmbedding(EmbeddingModel):
    """Maps specific known phrases to hand-picked vectors so cosine similarity
    behaves predictably in tests, without loading a real model. Unknown text maps
    to a fixed 'unrelated' vector far from the known cluster."""

    def __init__(self):
        self._known = {
            "what is rag?": np.array([1.0, 0.0, 0.0], dtype="float32"),
            "can you explain retrieval augmented generation?": np.array([0.98, 0.05, 0.0], dtype="float32"),
            "what is rag today?": np.array([1.0, 0.0, 0.0], dtype="float32"),
        }
        self._fallback = np.array([0.0, 1.0, 0.0], dtype="float32")

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.asarray([self._embed_one(t) for t in texts], dtype="float32")

    def _embed_one(self, text: str) -> np.ndarray:
        return self._known.get(text.lower().strip(), self._fallback)

    @property
    def dimension(self) -> int:
        return 3
