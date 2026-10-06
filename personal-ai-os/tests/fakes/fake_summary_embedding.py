import numpy as np

from app.retrieval.embeddings import EmbeddingModel


class FakeSummaryEmbedding(EmbeddingModel):
    """Purpose-built for memory-duplicate tests, hand-picked to mirror the
    REAL measured gap found while building this (see write_policy.py's
    is_semantic_duplicate docstring): a true paraphrase scores ~0.86 on
    the real model, a distinct memory scores well under 0.3. Deliberately
    a separate fixture from tests/fakes/fake_semantic_embedding.py (that
    one is for RAG-question caching tests) -- reusing an unrelated fake's
    hand-picked vectors here would risk the same real-vs-fake mismatch
    this project already caught once."""

    def __init__(self):
        self._known = {
            "learn docker in 30 days.": np.array([1.0, 0.0, 0.0], dtype="float32"),
            "user wants to learn docker within a month.": np.array([0.86, 0.1, 0.0], dtype="float32"),
            "chose rag over fine-tuning for the spec doc q&a feature.": np.array([0.0, 1.0, 0.0], dtype="float32"),
            "prefers dark mode in the dashboard ui.": np.array([0.0, 0.0, 1.0], dtype="float32"),
        }
        self._fallback = np.array([0.5, 0.5, 0.5], dtype="float32")

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.asarray([self._embed_one(t) for t in texts], dtype="float32")

    def _embed_one(self, text: str) -> np.ndarray:
        return self._known.get(text.lower().strip(), self._fallback)

    @property
    def dimension(self) -> int:
        return 3
