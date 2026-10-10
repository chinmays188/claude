"""Real conflict handling during memory consolidation -- found missing
while breaking context/memory down into retrieve/keep/forget plus the
user's further ask about "how conflicting info of the user is handled
during consolidation."

Checked first, honestly: `is_semantic_duplicate()` (write_policy.py) was
the only existing mechanism anywhere close to this, but it conflates two
genuinely different real outcomes under one boolean -- a near-identical
restatement ("Prefers dark mode." said twice) and a genuine contradiction
("Prefers dark mode." then later "Actually, prefers light mode now.")
both score high similarity and both get silently DROPPED, with the new
information never even written. That's correct for a restatement, wrong
for a contradiction -- a real contradiction should update what's
remembered, not be discarded in favor of stale information.

ConflictResolver distinguishes the two with a real LLM judgment call
(semantic similarity alone can't tell "same" from "opposite" -- a
paraphrase and a negation can both score high), then applies this
project's established never-destroy-on-write discipline: a genuine
conflict marks the OLD memory SUPERSEDED (never deleted, preserving
history, same pattern as memory decay flagging for review rather than
deleting) and lets the NEW one be written as the current truth. A high-
importance conflict routes through the SAME human-approval mechanism
MemoryWritePolicy already has for important writes, rather than a new,
separate approval path.
"""

from enum import Enum

from pydantic import BaseModel

from app.memory.models import MemoryRecord
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

CONFLICT_JUDGE_PROMPT = """You are deciding whether a NEW piece of information about a
user genuinely CONTRADICTS an EXISTING memory, or is merely a restatement/refinement of
the same fact (not a contradiction).

Existing memory: {existing_content}
New information: {new_content}

- CONTRADICTS: the new information is incompatible with the existing one (e.g. a stated
  preference flipped, a fact changed).
- SAME: the new information restates, rephrases, or refines the existing one without
  actually conflicting with it (e.g. adds detail, says the same thing differently).
- UNRELATED: the two aren't actually about the same thing (should not normally happen if
  this was flagged as semantically similar, but report it honestly if so).

Respond with ONLY a JSON object:
{{
  "verdict": "CONTRADICTS" | "SAME" | "UNRELATED",
  "reasoning": "<one sentence>"
}}
"""


class ConflictVerdict(str, Enum):
    CONTRADICTS = "CONTRADICTS"
    SAME = "SAME"
    UNRELATED = "UNRELATED"


class ConflictJudgment(BaseModel):
    verdict: ConflictVerdict
    reasoning: str


class ConflictResolution(BaseModel):
    """Real, inspectable outcome of one conflict check -- so a caller (or
    the dashboard) can show exactly what was decided and why, not just
    the final state."""

    judgment: ConflictJudgment
    existing_memory: MemoryRecord
    superseded: bool
    requires_approval: bool


class ConflictResolver:
    def __init__(self, llm: LLMProvider, approval_threshold: float = 0.7):
        self._llm = llm
        self._approval_threshold = approval_threshold

    def resolve(self, existing_memory: MemoryRecord, new_content: str, new_importance: float) -> ConflictResolution:
        """Judges whether new_content genuinely contradicts existing_memory.
        Returns a ConflictResolution describing the outcome -- the CALLER
        is responsible for actually calling PersistentMemoryStore.
        mark_superseded() and write() based on it (this function makes the
        decision; it doesn't touch storage, consistent with
        MemoryWritePolicy.evaluate()'s own separation of decision from
        persistence)."""
        generator = RepairableGenerator(self._llm, ConflictJudgment)
        judgment = generator.generate(
            CONFLICT_JUDGE_PROMPT.format(existing_content=existing_memory.content, new_content=new_content)
        )

        superseded = judgment.verdict == ConflictVerdict.CONTRADICTS
        requires_approval = superseded and new_importance >= self._approval_threshold

        return ConflictResolution(
            judgment=judgment, existing_memory=existing_memory,
            superseded=superseded, requires_approval=requires_approval,
        )
