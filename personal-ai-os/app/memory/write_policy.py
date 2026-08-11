from pydantic import BaseModel

from app.memory.models import MemoryType
from app.providers.base import LLMProvider
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
    Semantic duplicate detection (e.g. via embeddings) is not implemented in this
    milestone; this is the first-pass gate."""
    normalized_new = new_summary.strip().lower()
    return any(normalized_new == s.strip().lower() for s in existing_summaries)


class MemoryWritePolicy:
    """Implements Section 12's full pipeline: candidate -> classify -> importance
    -> duplicate check -> approval (if required) -> persist. The system must NOT
    save every conversation — this is the gate that decides what's worth keeping."""

    def __init__(self, llm: LLMProvider, importance_threshold: float = 0.3, approval_threshold: float = 0.7):
        self._llm = llm
        self._importance_threshold = importance_threshold
        self._approval_threshold = approval_threshold

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

        requires_approval = candidate.importance >= self._approval_threshold
        return candidate, requires_approval
