from datetime import datetime, timezone

from app.db.connection import get_connection
from app.memory.models import MemoryRecord, MemoryType
from app.memory.persistent_store import PersistentMemoryStore

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _record(memory_id: str, tenant="t1", user="u1", type_=MemoryType.GOAL, content="content") -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id, tenant_id=tenant, user_id=user, type=type_,
        content=content, source="conversation", created_at=NOW, updated_at=NOW,
    )


def _store() -> PersistentMemoryStore:
    return PersistentMemoryStore(get_connection(":memory:"))


def test_write_then_get():
    store = _store()
    store.write(_record("m1"))

    result = store.get("t1", "u1", "m1")

    assert result is not None
    assert result.memory_id == "m1"


def test_delete_removes_the_memory():
    store = _store()
    store.write(_record("m1"))

    store.delete("t1", "u1", "m1")

    assert store.get("t1", "u1", "m1") is None


def test_delete_is_scoped_to_tenant_and_user():
    store = _store()
    store.write(_record("m1", tenant="t1", user="u1"))

    store.delete("t2", "u2", "m1")  # wrong scope -- should not delete

    assert store.get("t1", "u1", "m1") is not None


def test_get_missing_returns_none():
    store = _store()

    assert store.get("t1", "u1", "does-not-exist") is None


def test_write_persists_across_store_instances_with_same_connection():
    conn = get_connection(":memory:")
    store1 = PersistentMemoryStore(conn)
    store1.write(_record("m1"))

    store2 = PersistentMemoryStore(conn)  # re-wraps the same connection
    result = store2.get("t1", "u1", "m1")

    assert result is not None


def test_list_all_scoped_to_tenant_and_user():
    store = _store()
    store.write(_record("m1", tenant="t1", user="u1"))
    store.write(_record("m2", tenant="t1", user="u2"))
    store.write(_record("m3", tenant="t2", user="u1"))

    results = store.list_all("t1", "u1")

    assert [r.memory_id for r in results] == ["m1"]


def test_list_by_type_filters_correctly():
    store = _store()
    store.write(_record("m1", type_=MemoryType.GOAL))
    store.write(_record("m2", type_=MemoryType.DECISION))

    results = store.list_by_type("t1", "u1", MemoryType.GOAL)

    assert [r.memory_id for r in results] == ["m1"]


def test_count_reflects_scoped_records():
    store = _store()
    store.write(_record("m1"))
    store.write(_record("m2"))
    store.write(_record("m3", tenant="other_tenant"))

    assert store.count("t1", "u1") == 2


def test_write_with_same_memory_id_upserts():
    store = _store()
    store.write(_record("m1", content="original"))
    store.write(_record("m1", content="updated"))

    result = store.get("t1", "u1", "m1")

    assert result.content == "updated"
    assert store.count("t1", "u1") == 1


def test_update_confidence_persists_new_value():
    store = _store()
    store.write(_record("m1"))

    store.update_confidence("t1", "u1", "m1", 0.42)

    assert store.get("t1", "u1", "m1").confidence == 0.42


def test_update_confidence_does_not_change_updated_at():
    store = _store()
    record = _record("m1")
    store.write(record)

    store.update_confidence("t1", "u1", "m1", 0.1)

    assert store.get("t1", "u1", "m1").updated_at == record.updated_at
