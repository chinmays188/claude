from datetime import datetime, timedelta, timezone

from app.db.connection import get_connection
from app.memory.decay import apply_decay, compute_decayed_confidence, find_decay_candidates
from app.memory.models import MemoryRecord, MemoryType
from app.memory.persistent_store import PersistentMemoryStore

NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def _memory(memory_id="m1", confidence=1.0, user_confirmed=False, age_days=0) -> MemoryRecord:
    updated_at = NOW - timedelta(days=age_days)
    return MemoryRecord(
        memory_id=memory_id, tenant_id="t1", user_id="u1", type=MemoryType.PREFERENCE,
        content="likes dark mode", source="conversation", confidence=confidence,
        created_at=updated_at, updated_at=updated_at, user_confirmed=user_confirmed,
    )


def test_confirmed_memory_never_decays():
    memory = _memory(confidence=1.0, user_confirmed=True, age_days=365)

    decayed = compute_decayed_confidence(memory, NOW, half_life_days=90.0)

    assert decayed == 1.0


def test_unconfirmed_memory_decays_by_half_at_the_half_life():
    memory = _memory(confidence=1.0, user_confirmed=False, age_days=90)

    decayed = compute_decayed_confidence(memory, NOW, half_life_days=90.0)

    assert abs(decayed - 0.5) < 1e-9


def test_fresh_unconfirmed_memory_barely_decays():
    memory = _memory(confidence=1.0, user_confirmed=False, age_days=0)

    decayed = compute_decayed_confidence(memory, NOW, half_life_days=90.0)

    assert abs(decayed - 1.0) < 1e-9


def test_find_decay_candidates_flags_low_confidence_unconfirmed_memories():
    old_unconfirmed = _memory("m1", confidence=1.0, user_confirmed=False, age_days=365)  # well decayed
    old_confirmed = _memory("m2", confidence=1.0, user_confirmed=True, age_days=365)  # never decays
    fresh_unconfirmed = _memory("m3", confidence=1.0, user_confirmed=False, age_days=1)

    candidates = find_decay_candidates(
        [old_unconfirmed, old_confirmed, fresh_unconfirmed], NOW, half_life_days=90.0, review_threshold=0.3
    )

    flagged_ids = {m.memory_id for m, _ in candidates}
    assert flagged_ids == {"m1"}


def test_find_decay_candidates_never_modifies_anything():
    memory = _memory("m1", confidence=1.0, user_confirmed=False, age_days=365)

    find_decay_candidates([memory], NOW, half_life_days=90.0)

    assert memory.confidence == 1.0  # untouched -- a pure read-only computation


def test_apply_decay_persists_real_updated_confidence():
    store = PersistentMemoryStore(get_connection(":memory:"))
    store.write(_memory("m1", confidence=1.0, user_confirmed=False, age_days=90))

    updated = apply_decay(store, "t1", "u1", NOW, half_life_days=90.0)

    assert len(updated) == 1
    persisted = store.get("t1", "u1", "m1")
    assert abs(persisted.confidence - 0.5) < 1e-9


def test_apply_decay_never_touches_updated_at():
    store = PersistentMemoryStore(get_connection(":memory:"))
    original = _memory("m1", confidence=1.0, user_confirmed=False, age_days=90)
    store.write(original)

    apply_decay(store, "t1", "u1", NOW, half_life_days=90.0)

    persisted = store.get("t1", "u1", "m1")
    assert persisted.updated_at == original.updated_at


def test_apply_decay_skips_confirmed_memories():
    store = PersistentMemoryStore(get_connection(":memory:"))
    store.write(_memory("m1", confidence=1.0, user_confirmed=True, age_days=365))

    updated = apply_decay(store, "t1", "u1", NOW, half_life_days=90.0)

    assert updated == []
    assert store.get("t1", "u1", "m1").confidence == 1.0
