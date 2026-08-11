import json
import sqlite3
from datetime import date, datetime

from app.graph.models import Decision, GraphEdge, GraphNode, NodeType

_SCHEMA = """
CREATE TABLE IF NOT EXISTS graph_nodes (
    node_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    type TEXT NOT NULL,
    label TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS graph_edges (
    edge_id TEXT PRIMARY KEY,
    from_node_id TEXT NOT NULL,
    to_node_id TEXT NOT NULL,
    relationship TEXT NOT NULL,
    FOREIGN KEY (from_node_id) REFERENCES graph_nodes(node_id),
    FOREIGN KEY (to_node_id) REFERENCES graph_nodes(node_id)
);
CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    date TEXT NOT NULL,
    context TEXT NOT NULL,
    reason TEXT NOT NULL,
    alternatives_json TEXT NOT NULL,
    chosen_option TEXT NOT NULL,
    expected_outcome TEXT NOT NULL,
    actual_outcome TEXT,
    related_project TEXT
);
"""


class NodeNotFoundError(Exception):
    pass


class DecisionNotFoundError(Exception):
    pass


class GraphStore:
    """SQLite-backed personal event/decision graph (Sections 32-33). Nodes and
    edges model People/Projects/Goals/Decisions/Experiences/Achievements/
    Documents/Tasks and their relationships; decisions get a dedicated table
    matching Section 33's exact schema, since 'why did I make this decision?'
    is the specifically-named query this milestone must answer."""

    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def add_node(self, node: GraphNode) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO graph_nodes (node_id, owner_id, type, label, created_at) VALUES (?, ?, ?, ?, ?)",
            (node.node_id, node.owner_id, node.type.value, node.label, node.created_at.isoformat()),
        )
        self._conn.commit()

    def get_node(self, node_id: str) -> GraphNode:
        row = self._conn.execute("SELECT * FROM graph_nodes WHERE node_id = ?", (node_id,)).fetchone()
        if row is None:
            raise NodeNotFoundError(f"No node with id '{node_id}'.")
        return GraphNode(
            node_id=row["node_id"], owner_id=row["owner_id"], type=NodeType(row["type"]),
            label=row["label"], created_at=datetime.fromisoformat(row["created_at"]),
        )

    def add_edge(self, edge: GraphEdge) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO graph_edges (edge_id, from_node_id, to_node_id, relationship) VALUES (?, ?, ?, ?)",
            (edge.edge_id, edge.from_node_id, edge.to_node_id, edge.relationship),
        )
        self._conn.commit()

    def neighbors(self, node_id: str) -> list[GraphNode]:
        rows = self._conn.execute(
            "SELECT to_node_id FROM graph_edges WHERE from_node_id = ?", (node_id,)
        ).fetchall()
        return [self.get_node(row["to_node_id"]) for row in rows]

    def nodes_by_type(self, owner_id: str, node_type: NodeType) -> list[GraphNode]:
        rows = self._conn.execute(
            "SELECT * FROM graph_nodes WHERE owner_id = ? AND type = ? ORDER BY created_at DESC",
            (owner_id, node_type.value),
        ).fetchall()
        return [
            GraphNode(node_id=r["node_id"], owner_id=r["owner_id"], type=NodeType(r["type"]), label=r["label"], created_at=datetime.fromisoformat(r["created_at"]))
            for r in rows
        ]

    def add_decision(self, decision: Decision) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO decisions
               (decision_id, owner_id, decision, date, context, reason, alternatives_json,
                chosen_option, expected_outcome, actual_outcome, related_project)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                decision.decision_id, decision.owner_id, decision.decision, decision.date.isoformat(),
                decision.context, decision.reason, json.dumps(decision.alternatives),
                decision.chosen_option, decision.expected_outcome, decision.actual_outcome,
                decision.related_project,
            ),
        )
        self._conn.commit()

    def get_decision(self, decision_id: str) -> Decision:
        row = self._conn.execute("SELECT * FROM decisions WHERE decision_id = ?", (decision_id,)).fetchone()
        if row is None:
            raise DecisionNotFoundError(f"No decision with id '{decision_id}'.")
        return _row_to_decision(row)

    def why(self, decision_id: str) -> str:
        """Answers Section 33's exact question: 'Why did I make this decision?'"""
        decision = self.get_decision(decision_id)
        return (
            f"On {decision.date}, you decided: {decision.decision}\n"
            f"Context: {decision.context}\n"
            f"Reason: {decision.reason}\n"
            f"Chosen option: {decision.chosen_option}"
            + (f" (over: {', '.join(decision.alternatives)})" if decision.alternatives else "")
            + f"\nExpected outcome: {decision.expected_outcome}"
            + (f"\nActual outcome: {decision.actual_outcome}" if decision.actual_outcome else "")
        )

    def decisions_for_project(self, owner_id: str, project_node_id: str) -> list[Decision]:
        rows = self._conn.execute(
            "SELECT * FROM decisions WHERE owner_id = ? AND related_project = ? ORDER BY date DESC",
            (owner_id, project_node_id),
        ).fetchall()
        return [_row_to_decision(row) for row in rows]


def _row_to_decision(row: sqlite3.Row) -> Decision:
    return Decision(
        decision_id=row["decision_id"], owner_id=row["owner_id"], decision=row["decision"],
        date=date.fromisoformat(row["date"]), context=row["context"], reason=row["reason"],
        alternatives=json.loads(row["alternatives_json"]), chosen_option=row["chosen_option"],
        expected_outcome=row["expected_outcome"], actual_outcome=row["actual_outcome"],
        related_project=row["related_project"],
    )
