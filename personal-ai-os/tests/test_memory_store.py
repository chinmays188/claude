from app.memory.store import MemoryStore


def test_write_then_read_same_scope():
    store = MemoryStore()

    store.write("tenant1", "user1", "session1", "goal", "learn docker")
    value = store.read("tenant1", "user1", "session1", "goal")

    assert value == "learn docker"


def test_read_missing_key_returns_none():
    store = MemoryStore()

    assert store.read("t1", "u1", "s1", "nonexistent") is None


def test_different_users_do_not_see_each_others_memory():
    store = MemoryStore()
    store.write("tenant1", "userA", "session1", "goal", "userA's goal")
    store.write("tenant1", "userB", "session1", "goal", "userB's goal")

    assert store.read("tenant1", "userA", "session1", "goal") == "userA's goal"
    assert store.read("tenant1", "userB", "session1", "goal") == "userB's goal"


def test_different_tenants_do_not_see_each_others_memory_even_with_same_user_id():
    store = MemoryStore()
    store.write("tenantA", "user1", "session1", "goal", "tenantA's data")
    store.write("tenantB", "user1", "session1", "goal", "tenantB's data")

    assert store.read("tenantA", "user1", "session1", "goal") == "tenantA's data"
    assert store.read("tenantB", "user1", "session1", "goal") == "tenantB's data"


def test_different_sessions_for_same_user_are_isolated():
    store = MemoryStore()
    store.write("t1", "u1", "session1", "topic", "docker")
    store.write("t1", "u1", "session2", "topic", "kubernetes")

    assert store.read("t1", "u1", "session1", "topic") == "docker"
    assert store.read("t1", "u1", "session2", "topic") == "kubernetes"


def test_list_keys_scoped_to_exact_tenant_user_session():
    store = MemoryStore()
    store.write("t1", "u1", "s1", "a", "1")
    store.write("t1", "u1", "s1", "b", "2")
    store.write("t1", "u2", "s1", "c", "3")

    keys = store.list_keys("t1", "u1", "s1")

    assert sorted(keys) == ["a", "b"]
