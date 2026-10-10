from datetime import datetime, timezone

from app.db.connection import get_connection
from app.graph.models import NodeType
from app.graph.store import GraphStore
from app.memory.graph_bridge import MemoryGraphBridge
from app.memory.models import MemoryRecord, MemoryType
from app.memory.persistent_store import PersistentMemoryStore

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _memory(memory_id: str, content: str) -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id, tenant_id="t1", user_id="alice", type=MemoryType.DECISION,
        content=content, source="conversation", created_at=NOW, updated_at=NOW,
    )


def _bridge():
    conn = get_connection(":memory:")
    graph_store = GraphStore(conn)
    memory_store = PersistentMemoryStore(conn)
    bridge = MemoryGraphBridge(graph_store, memory_store)
    return bridge, memory_store


def test_link_memory_creates_a_real_memory_type_graph_node():
    bridge, memory_store = _bridge()
    memory = _memory("m1", "Chose RAG over fine-tuning.")
    memory_store.write(memory)

    node = bridge.link_memory(memory)

    assert node.type == NodeType.MEMORY
    assert node.label == "m1"


def test_related_memories_follows_a_real_graph_edge_not_content_similarity():
    """The real point of hybrid storage: these two memories share almost
    no words in common (so vector similarity alone would likely miss
    the connection), but a real graph edge still correctly connects
    them, because the relationship is explicit, not content-derived."""
    bridge, memory_store = _bridge()
    decision_memory = _memory("m1", "Chose RAG over fine-tuning for the personal AI OS project.")
    goal_memory = _memory("m2", "Wants to ship a working AI PM learning project by year end.")
    memory_store.write(decision_memory)
    memory_store.write(goal_memory)

    decision_node = bridge.link_memory(decision_memory)
    goal_node = bridge.link_memory(goal_memory)
    bridge.relate(decision_node, goal_node, relationship="supports")

    related = bridge.related_memories("t1", "alice", decision_node.node_id)

    assert len(related) == 1
    assert related[0].memory_id == "m2"


def test_related_memories_returns_empty_list_for_an_unconnected_memory():
    bridge, memory_store = _bridge()
    memory = _memory("m1", "Chose RAG over fine-tuning.")
    memory_store.write(memory)
    node = bridge.link_memory(memory)

    related = bridge.related_memories("t1", "alice", node.node_id)

    assert related == []
