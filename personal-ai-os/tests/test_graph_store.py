from datetime import date

import pytest

from app.db.connection import get_connection
from app.graph.models import Decision, GraphEdge, GraphNode, NodeType
from app.graph.store import DecisionNotFoundError, GraphStore, NodeNotFoundError


def _store() -> GraphStore:
    return GraphStore(get_connection(":memory:"))


def test_add_and_get_node():
    store = _store()
    node = GraphNode(owner_id="alice", type=NodeType.PROJECT, label="Personal AI OS")
    store.add_node(node)

    result = store.get_node(node.node_id)

    assert result.label == "Personal AI OS"


def test_get_missing_node_raises():
    store = _store()

    with pytest.raises(NodeNotFoundError):
        store.get_node("does-not-exist")


def test_neighbors_traverses_edges():
    store = _store()
    user = GraphNode(owner_id="alice", type=NodeType.PERSON, label="Alice")
    project = GraphNode(owner_id="alice", type=NodeType.PROJECT, label="Personal AI OS")
    store.add_node(user)
    store.add_node(project)
    store.add_edge(GraphEdge(from_node_id=user.node_id, to_node_id=project.node_id, relationship="works_on"))

    neighbors = store.neighbors(user.node_id)

    assert len(neighbors) == 1
    assert neighbors[0].label == "Personal AI OS"


def test_nodes_by_type_filters_correctly():
    store = _store()
    store.add_node(GraphNode(owner_id="alice", type=NodeType.PROJECT, label="Project A"))
    store.add_node(GraphNode(owner_id="alice", type=NodeType.GOAL, label="Goal A"))
    store.add_node(GraphNode(owner_id="bob", type=NodeType.PROJECT, label="Project B"))

    projects = store.nodes_by_type("alice", NodeType.PROJECT)

    assert len(projects) == 1
    assert projects[0].label == "Project A"


def test_add_and_get_decision():
    store = _store()
    decision = Decision(
        owner_id="alice", decision="Use RAG for spec Q&A", date=date(2026, 8, 1),
        context="Spec doc changes frequently", reason="RAG stays fresh without retraining",
        alternatives=["fine-tuning", "in-context learning"], chosen_option="RAG",
        expected_outcome="Accurate, up-to-date answers with citations",
    )
    store.add_decision(decision)

    result = store.get_decision(decision.decision_id)

    assert result.chosen_option == "RAG"
    assert "fine-tuning" in result.alternatives


def test_get_missing_decision_raises():
    store = _store()

    with pytest.raises(DecisionNotFoundError):
        store.get_decision("does-not-exist")


def test_why_answers_the_decision_question():
    store = _store()
    decision = Decision(
        owner_id="alice", decision="Use RAG for spec Q&A", date=date(2026, 8, 1),
        context="Spec doc changes frequently", reason="RAG stays fresh without retraining",
        chosen_option="RAG", expected_outcome="Accurate answers",
    )
    store.add_decision(decision)

    explanation = store.why(decision.decision_id)

    assert "RAG stays fresh without retraining" in explanation
    assert "Use RAG for spec Q&A" in explanation


def test_why_includes_actual_outcome_when_known():
    store = _store()
    decision = Decision(
        owner_id="alice", decision="Use RAG", date=date(2026, 8, 1), context="c", reason="r",
        chosen_option="RAG", expected_outcome="expected", actual_outcome="Worked well, citations were accurate.",
    )
    store.add_decision(decision)

    explanation = store.why(decision.decision_id)

    assert "Worked well, citations were accurate." in explanation


def test_decisions_for_project_scoped_correctly():
    store = _store()
    project = GraphNode(owner_id="alice", type=NodeType.PROJECT, label="Personal AI OS")
    store.add_node(project)
    store.add_decision(
        Decision(
            owner_id="alice", decision="Use RAG", date=date(2026, 8, 1), context="c", reason="r",
            chosen_option="RAG", expected_outcome="e", related_project=project.node_id,
        )
    )
    store.add_decision(
        Decision(owner_id="alice", decision="Unrelated decision", date=date(2026, 7, 1), context="c", reason="r", chosen_option="X", expected_outcome="e")
    )

    decisions = store.decisions_for_project("alice", project.node_id)

    assert len(decisions) == 1
    assert decisions[0].decision == "Use RAG"


def test_graph_survives_across_store_instances_with_same_connection():
    conn = get_connection(":memory:")
    store1 = GraphStore(conn)
    node = GraphNode(owner_id="alice", type=NodeType.PROJECT, label="Test Project")
    store1.add_node(node)

    store2 = GraphStore(conn)
    result = store2.get_node(node.node_id)

    assert result.label == "Test Project"
