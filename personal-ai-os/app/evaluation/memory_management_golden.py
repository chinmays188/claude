"""Real, hand-crafted golden cases for memory MANAGEMENT -- retrieval,
decay, and conflict resolution. Each case states a scenario and a
human-judged correct outcome BEFORE looking at what the real code
produces, same discipline as context_engine_golden.py.
"""

from datetime import datetime, timedelta, timezone

from app.memory.conflict_resolution import ConflictVerdict
from app.memory.models import MemoryRecord, MemoryType
from app.evaluation.memory_management_eval import ConflictGoldenCase, DecayGoldenCase, RetrievalGoldenCase

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)


def _memory(memory_id: str, content: str, memory_type: MemoryType, age_days: float, importance: float = 0.5, confirmed: bool = False) -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id, tenant_id="t1", user_id="alice", type=memory_type,
        content=content, source="test", created_at=NOW - timedelta(days=age_days),
        updated_at=NOW - timedelta(days=age_days), importance=importance, user_confirmed=confirmed,
    )


RETRIEVAL_GOLDEN_CASES = [
    RetrievalGoldenCase(
        id="relevant_memory_beats_unrelated_memory",
        description="A query about RAG should retrieve the RAG-related memory over an "
                    "unrelated hobby memory, even though the hobby memory is more recent.",
        query="How should I explain RAG to a stakeholder?",
        candidates=[
            _memory("m1", "Chose RAG over fine-tuning for the personal AI OS project.", MemoryType.DECISION, age_days=30),
            _memory("m2", "Enjoys hiking on weekends.", MemoryType.EXPERIENCE, age_days=1),
        ],
        top_k=1,
        expected_retrieved_ids=["m1"],
        expected_excluded_ids=["m2"],
    ),
    RetrievalGoldenCase(
        id="user_confirmed_memory_ranks_above_unconfirmed_at_similar_relevance",
        description="Given two similarly-relevant memories about the same topic, the "
                    "user_confirmed one should rank first.",
        query="What are the user's communication preferences?",
        candidates=[
            _memory("m1", "Prefers concise, bullet-point answers.", MemoryType.PREFERENCE, age_days=10, confirmed=True),
            _memory("m2", "Might prefer shorter answers, inferred from one message.", MemoryType.PREFERENCE, age_days=10, confirmed=False),
        ],
        top_k=1,
        expected_retrieved_ids=["m1"],
        expected_excluded_ids=[],
    ),
]


DECAY_GOLDEN_CASES = [
    DecayGoldenCase(
        id="old_unconfirmed_memory_decays_significantly",
        description="An unconfirmed memory at exactly its half-life age should decay to "
                    "roughly half its original confidence -- well below a 0.7 threshold.",
        memory=_memory("m1", "Possibly interested in hiking.", MemoryType.EXPERIENCE, age_days=90, confirmed=False),
        as_of=NOW,
        half_life_days=90.0,
        expect_decayed_below=0.7,
    ),
    DecayGoldenCase(
        id="user_confirmed_memory_never_decays",
        description="A user_confirmed memory at the same age must NOT decay -- a human "
                    "already validated it, so its confidence should stay at 1.0.",
        memory=_memory("m1", "Definitely prefers dark mode (confirmed by user).", MemoryType.PREFERENCE, age_days=365, confirmed=True),
        as_of=NOW,
        half_life_days=90.0,
        expect_decayed_below=None,
    ),
]


CONFLICT_GOLDEN_CASES = [
    ConflictGoldenCase(
        id="contradiction_with_high_importance_requires_approval",
        description="A genuine contradiction about an important fact (e.g. a career goal "
                    "change) must require human approval before superseding.",
        verdict=ConflictVerdict.CONTRADICTS,
        new_importance=0.9,
        approval_threshold=0.7,
        expect_superseded=True,
        expect_requires_approval=True,
    ),
    ConflictGoldenCase(
        id="contradiction_with_low_importance_does_not_require_approval",
        description="A genuine but low-importance contradiction (e.g. a minor preference) "
                    "should supersede automatically, without needing human approval.",
        verdict=ConflictVerdict.CONTRADICTS,
        new_importance=0.3,
        approval_threshold=0.7,
        expect_superseded=True,
        expect_requires_approval=False,
    ),
    ConflictGoldenCase(
        id="non_contradiction_never_supersedes_regardless_of_importance",
        description="A restatement (SAME verdict) must never supersede the existing "
                    "memory, even if importance is high -- superseding is reserved for "
                    "genuine contradictions only.",
        verdict=ConflictVerdict.SAME,
        new_importance=0.95,
        approval_threshold=0.7,
        expect_superseded=False,
        expect_requires_approval=False,
    ),
]
