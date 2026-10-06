"""Real memory decay/update, found missing while investigating "AI
Memory": PersistentMemoryStore's confidence/importance fields never
changed over time, and MemoryRetriever's recency scoring only affects
retrieval RANKING -- an old memory scores lower but is never actually
updated, flagged, or removed. This module closes that gap.

Confirmed memories (user_confirmed=True) don't decay: the human
explicitly validated them, so staleness from age alone isn't the same
signal as for an unconfirmed, inferred memory. Same half-life decay
pattern MemoryRetriever already uses for recency scoring (Section 13),
applied here to confidence instead of a ranking score. Never
auto-deletes anything -- matches this project's standing human-in-the-
loop principle (the same reason MemoryWritePolicy queues high-importance
writes for approval instead of auto-writing them): decay only flags a
review candidate, a human decides what happens to it.
"""

from datetime import datetime, timezone

from app.memory.models import MemoryRecord
from app.memory.persistent_store import PersistentMemoryStore


def compute_decayed_confidence(memory: MemoryRecord, as_of: datetime, half_life_days: float = 90.0) -> float:
    """Real confidence decay for unconfirmed memories, by age since
    updated_at. Confirmed memories return their confidence unchanged --
    a human already validated them, so this function has nothing to
    correct for age alone."""
    if memory.user_confirmed:
        return memory.confidence

    updated_at = memory.updated_at
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    age_days = max((as_of - updated_at).total_seconds() / 86400, 0)
    decay_factor = 0.5 ** (age_days / half_life_days)
    return memory.confidence * decay_factor


def find_decay_candidates(
    memories: list[MemoryRecord], as_of: datetime, half_life_days: float = 90.0, review_threshold: float = 0.3
) -> list[tuple[MemoryRecord, float]]:
    """Real candidates for human review -- unconfirmed memories whose
    decayed confidence has dropped below review_threshold. Returns
    (memory, decayed_confidence) pairs; never deletes or modifies
    anything itself."""
    candidates = []
    for memory in memories:
        decayed = compute_decayed_confidence(memory, as_of, half_life_days)
        if decayed < review_threshold:
            candidates.append((memory, decayed))
    return candidates


def apply_decay(
    store: PersistentMemoryStore, tenant_id: str, user_id: str, as_of: datetime, half_life_days: float = 90.0,
) -> list[tuple[MemoryRecord, float]]:
    """Real, persisted decay pass over every memory in scope: computes
    each unconfirmed memory's decayed confidence and writes it back via
    update_confidence() (confirmed memories are read but left untouched,
    per compute_decayed_confidence()'s own rule). Returns the same
    (memory, decayed_confidence) pairs that were written, so a caller
    (e.g. a scheduled job or the dashboard) can report what changed."""
    updated = []
    for memory in store.list_all(tenant_id, user_id):
        decayed = compute_decayed_confidence(memory, as_of, half_life_days)
        if decayed != memory.confidence:
            store.update_confidence(tenant_id, user_id, memory.memory_id, decayed)
            updated.append((memory, decayed))
    return updated
