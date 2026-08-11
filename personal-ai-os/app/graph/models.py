import uuid
from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    PERSON = "person"
    PROJECT = "project"
    GOAL = "goal"
    DECISION = "decision"
    EXPERIENCE = "experience"
    ACHIEVEMENT = "achievement"
    DOCUMENT = "document"
    TASK = "task"


class GraphNode(BaseModel):
    node_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    owner_id: str
    type: NodeType
    label: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GraphEdge(BaseModel):
    edge_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    from_node_id: str
    to_node_id: str
    relationship: str  # e.g. "works_on", "achieved", "relates_to"


class Decision(BaseModel):
    """Section 33's exact decision record shape. related_project links back
    into the graph via a GraphNode id, so a decision can be traversed from
    its project or vice versa."""

    decision_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    owner_id: str
    decision: str
    date: date
    context: str
    reason: str
    alternatives: list[str] = Field(default_factory=list)
    chosen_option: str
    expected_outcome: str
    actual_outcome: str | None = None
    related_project: str | None = None  # GraphNode.node_id of a PROJECT node
