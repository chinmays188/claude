from pydantic import BaseModel

from app.memory.models import MemoryType
from app.providers.base import LLMProvider
from app.retrieval.embeddings import EmbeddingModel
from app.structured.repair import RepairableGenerator

CLASSIFY_PROMPT = """Decide whether the following piece of conversation is worth
remembering as long-term personal memory, and if so, what type and how important.

Not every message deserves to be remembered — small talk, one-off questions with
no lasting relevance, and purely transactional exchanges should NOT be saved.

Conversation excerpt: {text}

Respond with ONLY a JSON object:
{{
  "should_remember": true | false,
  "type": "profile" | "preference" | "goal" | "decision" | "experience" | "achievement" | "project" | "relationship" | "learning" | null,
  "importance": 0.0-1.0,
  "summary": "<a short, memory-worthy summary, or null if should_remember is false>"
}}
"""


class MemoryCandidate(BaseModel):
    should_remember: bool
    type: MemoryType | None = None
    importance: float = 0.0
    summary: str | None = None


def classify_for_memory(llm: LLMProvider, conversation_text: str) -> MemoryCandidate:
    generator = RepairableGenerator(llm, MemoryCandidate)
    return generator.generate(CLASSIFY_PROMPT.format(text=conversation_text))


def is_duplicate(new_summary: str, existing_summaries: list[str]) -> bool:
    """Section 12's 'Duplicate Check' step. Exact (case/whitespace-insensitive)
    match — a deliberately simple, cheap check before writing anything permanent.
    Kept as the always-available first-pass gate (catches a literal re-save with
    zero embedding cost); see is_semantic_duplicate() below for the real
    embedding-based check this milestone originally left out."""
    normalized_new = new_summary.strip().lower()
    return any(normalized_new == s.strip().lower() for s in existing_summaries)


def is_semantic_duplicate(
    embedding_model: EmbeddingModel, new_summary: str, existing_summaries: list[str], threshold: float = 0.8
) -> bool:
    """Found missing while investigating 'AI Memory': the module's own
    docstring admitted semantic duplicate detection wasn't implemented.
    Real cosine similarity over real sentence-transformer embeddings --
    threshold re-measured against the REAL model, not assumed (same
    discipline as the semantic cache's threshold fix): a true paraphrase
    ("Learn Docker in 30 days." vs. "User wants to learn Docker within a
    month.") scores a real 0.857, while every genuinely distinct pair
    tried stayed below 0.3 -- 0.8 is a real, defensible margin, not a
    round-number guess."""
    if not existing_summaries:
        return False
    import numpy as np

    new_vec = embedding_model.embed([new_summary])[0]
    existing_vecs = embedding_model.embed(existing_summaries)
    for existing_vec in existing_vecs:
        denom = np.linalg.norm(new_vec) * np.linalg.norm(existing_vec)
        similarity = float(np.dot(new_vec, existing_vec) / denom) if denom else 0.0
        if similarity >= threshold:
            return True
    return False


class MemoryWritePolicy:
    """Implements Section 12's full pipeline: candidate -> classify -> importance
    -> duplicate check -> approval (if required) -> persist. The system must NOT
    save every conversation — this is the gate that decides what's worth keeping."""

    def __init__(
        self,
        llm: LLMProvider,
        importance_threshold: float = 0.3,
        approval_threshold: float = 0.7,
        embedding_model: EmbeddingModel | None = None,
        semantic_duplicate_threshold: float = 0.8,
    ):
        self._llm = llm
        self._importance_threshold = importance_threshold
        self._approval_threshold = approval_threshold
        # Optional, additive -- found missing (module docstring admitted
        # it), backward-compatible for every existing caller that doesn't
        # pass one: duplicate check stays exact-match-only as before.
        self._embedding_model = embedding_model
        self._semantic_duplicate_threshold = semantic_duplicate_threshold

    def evaluate(self, conversation_text: str, existing_summaries: list[str]) -> tuple[MemoryCandidate | None, bool]:
        """Returns (candidate, requires_approval). candidate is None if nothing
        should be remembered at all (below importance threshold, a duplicate,
        or the classifier decided it isn't memory-worthy)."""
        candidate = classify_for_memory(self._llm, conversation_text)

        if not candidate.should_remember:
            return None, False

        if candidate.importance < self._importance_threshold:
            return None, False

        if candidate.summary and is_duplicate(candidate.summary, existing_summaries):
            return None, False

        if candidate.summary and self._embedding_model is not None and is_semantic_duplicate(
            self._embedding_model, candidate.summary, existing_summaries, self._semantic_duplicate_threshold
        ):
            return None, False

        requires_approval = candidate.importance >= self._approval_threshold
        return candidate, requires_approval
