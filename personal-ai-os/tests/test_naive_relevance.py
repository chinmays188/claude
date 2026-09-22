import sqlite3
from datetime import datetime, timezone

from app.memory.models import MemoryRecord, MemoryType
from app.memory.naive_relevance import find_relevant_memories
from app.memory.persistent_store import PersistentMemoryStore

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _store_with_memories():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = PersistentMemoryStore(conn)
    store.write(MemoryRecord(
        memory_id="m1", tenant_id="t1", user_id="u1", type=MemoryType.GOAL,
        content="Wants to become an AI PM within 12 months.", source="test",
        created_at=NOW, updated_at=NOW,
    ))
    store.write(MemoryRecord(
        memory_id="m2", tenant_id="t1", user_id="u1", type=MemoryType.LEARNING,
        content="Currently studying Kubernetes fundamentals.", source="test",
        created_at=NOW, updated_at=NOW,
    ))
    store.write(MemoryRecord(
        memory_id="m3", tenant_id="t1", user_id="u1", type=MemoryType.PREFERENCE,
        content="Prefers concise, bullet-point explanations.", source="test",
        created_at=NOW, updated_at=NOW,
    ))
    return store


def test_finds_memory_with_keyword_overlap():
    store = _store_with_memories()

    results = find_relevant_memories(store, "t1", "u1", "Should I learn Kubernetes for my career?")

    memory_ids = [m.memory_id for m, _ in results]
    assert "m2" in memory_ids  # shares "kubernetes"


def test_returns_empty_when_no_keyword_overlap():
    store = _store_with_memories()

    results = find_relevant_memories(store, "t1", "u1", "What's the weather like today?")

    assert results == []


def test_ranks_by_overlap_count_descending():
    store = _store_with_memories()

    results = find_relevant_memories(store, "t1", "u1", "AI PM career goals and Kubernetes learning")

    overlaps = [count for _, count in results]
    assert overlaps == sorted(overlaps, reverse=True)


def test_respects_top_k():
    store = _store_with_memories()

    results = find_relevant_memories(store, "t1", "u1", "AI PM career Kubernetes bullet points", top_k=1)

    assert len(results) == 1


def test_empty_query_returns_no_memories():
    store = _store_with_memories()

    results = find_relevant_memories(store, "t1", "u1", "the a of")  # all stopwords

    assert results == []
