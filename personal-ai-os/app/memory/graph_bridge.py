"""Real hybrid (vector + graph) memory storage -- found missing while
breaking context/memory down into retrieve/keep/forget plus the user's
further ask about "different types of storage architectures of memory -
vector db, knowledge graph, hybrid."

Checked first, honestly: this project has real vector similarity over
memory content (MemoryRetriever, computed on-the-fly via embeddings --
"what to RETRIEVE") and a real, separate GraphStore (nodes/edges,
Section 33's decision graph) -- but GraphStore was wired ONLY to
decisions/goals/projects, never to personal MemoryRecords. There was no
real hybrid capability: vector search alone can find a memory similar to
a query, but can't answer "what is THIS memory connected to" (e.g. a
DECISION memory that supports a particular GOAL memory) -- that needs a
real graph traversal, which plain cosine similarity can't do.

MemoryGraphBridge closes it with pure composition over the existing,
unchanged GraphStore: one real GraphNode per linked MemoryRecord
(type=NodeType.MEMORY, label=memory_id so a traversal result maps back
to the real record), and real GraphEdges between memories with an
explicit relationship label (e.g. "supports", "relates_to"). No new
storage layer -- the SQLite-backed GraphStore already exists and is
already tested.
"""

from app.graph.models import GraphEdge, GraphNode, NodeType
from app.graph.store import GraphStore
from app.memory.models import MemoryRecord
from app.memory.persistent_store import PersistentMemoryStore


class MemoryGraphBridge:
    def __init__(self, graph_store: GraphStore, memory_store: PersistentMemoryStore):
        self._graph = graph_store
        self._memory_store = memory_store

    def link_memory(self, memory: MemoryRecord) -> GraphNode:
        """Real, idempotent: creates (or re-creates, if called again) a
        GraphNode for this memory. label=memory_id, not memory.content --
        content can be long/change; the node's whole job is to be a
        stable graph-side handle back to the real memory_id."""
        node = GraphNode(owner_id=memory.user_id, type=NodeType.MEMORY, label=memory.memory_id)
        self._graph.add_node(node)
        return node

    def relate(self, from_node: GraphNode, to_node: GraphNode, relationship: str) -> GraphEdge:
        """Real graph edge between two already-linked memory nodes
        (e.g. a DECISION memory that "supports" a GOAL memory)."""
        edge = GraphEdge(from_node_id=from_node.node_id, to_node_id=to_node.node_id, relationship=relationship)
        self._graph.add_edge(edge)
        return edge

    def related_memories(self, tenant_id: str, user_id: str, node_id: str) -> list[MemoryRecord]:
        """Real hybrid traversal: given a graph node for one memory,
        returns the real MemoryRecords it's connected to -- genuinely
        different from vector similarity, which only ever finds memories
        similar IN CONTENT to a query, never memories connected by an
        explicit real relationship regardless of content similarity."""
        neighbor_nodes = self._graph.neighbors(node_id)
        related = []
        for neighbor in neighbor_nodes:
            if neighbor.type != NodeType.MEMORY:
                continue
            memory = self._memory_store.get(tenant_id, user_id, neighbor.label)
            if memory is not None:
                related.append(memory)
        return related
