from datetime import date, datetime, timezone

from app.actions.audit_log import AuditLog
from app.actions.models import ActionClass, ActionProposal, ApprovalStatus, AuditRecord
from app.dashboard.data import (
    get_ai_health,
    get_dashboard_snapshot,
    get_memory_summary,
    get_todays_activity,
)
from app.db.connection import get_connection
from app.graph.models import GraphNode, NodeType
from app.graph.store import GraphStore
from app.memory.models import MemoryRecord, MemoryType
from app.memory.persistent_store import PersistentMemoryStore
from app.observability.traces import Trace
from app.tasks.models import LongRunningTask, TaskState
from app.tasks.store import TaskStore

NOW = datetime.now(timezone.utc)
TODAY = NOW.date()


def _trace(status="success", latency_ms=100.0) -> Trace:
    return Trace(session_id="s1", user_id="alice", status=status, latency_ms=latency_ms)


def test_todays_activity_counts_agent_runs():
    audit_log = AuditLog(get_connection(":memory:"))
    task_store = TaskStore(get_connection(":memory:"))
    traces = [_trace(), _trace(), _trace(status="error")]

    activity = get_todays_activity(traces, audit_log, task_store, owner="alice", today=TODAY)

    assert activity.agent_runs == 3
    assert activity.evaluation_score == 2 / 3


def test_todays_activity_counts_completed_tasks():
    audit_log = AuditLog(get_connection(":memory:"))
    task_store = TaskStore(get_connection(":memory:"))
    task = LongRunningTask(owner="alice", description="Research")
    task_store.create(task)
    task_store.transition(task.task_id, TaskState.PLANNING)
    task_store.transition(task.task_id, TaskState.RUNNING)
    task_store.transition(task.task_id, TaskState.COMPLETED)

    activity = get_todays_activity([], audit_log, task_store, owner="alice", today=TODAY)

    assert activity.tasks_completed == 1


def test_todays_activity_counts_pending_approvals():
    audit_log = AuditLog(get_connection(":memory:"))
    task_store = TaskStore(get_connection(":memory:"))
    proposal = ActionProposal(action_class=ActionClass.ACT, tool_name="send_email", description="d", args={})
    audit_log.record(AuditRecord(action_id=proposal.action_id, proposal=proposal, approval_status=ApprovalStatus.PENDING))

    activity = get_todays_activity([], audit_log, task_store, owner="alice", today=TODAY)

    assert activity.pending_approvals == 1


def test_todays_activity_avg_latency():
    audit_log = AuditLog(get_connection(":memory:"))
    task_store = TaskStore(get_connection(":memory:"))
    traces = [_trace(latency_ms=100.0), _trace(latency_ms=200.0)]

    activity = get_todays_activity(traces, audit_log, task_store, owner="alice", today=TODAY)

    assert activity.avg_latency_ms == 150.0


def test_todays_activity_handles_no_traces_gracefully():
    audit_log = AuditLog(get_connection(":memory:"))
    task_store = TaskStore(get_connection(":memory:"))

    activity = get_todays_activity([], audit_log, task_store, owner="alice", today=TODAY)

    assert activity.agent_runs == 0
    assert activity.evaluation_score is None
    assert activity.avg_latency_ms is None


def test_memory_summary_counts_memories_decisions_projects():
    memory_store = PersistentMemoryStore(get_connection(":memory:"))
    graph_store = GraphStore(get_connection(":memory:"))
    memory_store.write(MemoryRecord(memory_id="m1", tenant_id="t1", user_id="alice", type=MemoryType.GOAL, content="x", source="s", created_at=NOW, updated_at=NOW))
    graph_store.add_node(GraphNode(owner_id="alice", type=NodeType.DECISION, label="Decision 1"))
    graph_store.add_node(GraphNode(owner_id="alice", type=NodeType.PROJECT, label="Project 1"))
    graph_store.add_node(GraphNode(owner_id="alice", type=NodeType.PROJECT, label="Project 2"))

    summary = get_memory_summary(memory_store, graph_store, "t1", "alice")

    assert summary.memories == 1
    assert summary.decisions == 1
    assert summary.projects == 2


def test_ai_health_regression_status_pass():
    health = get_ai_health(groundedness=0.94, regression_passed=True)

    assert health.regression_status == "PASS"
    assert health.groundedness == 0.94


def test_ai_health_regression_status_fail():
    health = get_ai_health(regression_passed=False)

    assert health.regression_status == "FAIL"


def test_ai_health_regression_status_unknown_by_default():
    health = get_ai_health()

    assert health.regression_status == "UNKNOWN"


def test_dashboard_snapshot_assembles_all_sections():
    audit_log = AuditLog(get_connection(":memory:"))
    task_store = TaskStore(get_connection(":memory:"))
    memory_store = PersistentMemoryStore(get_connection(":memory:"))
    graph_store = GraphStore(get_connection(":memory:"))

    snapshot = get_dashboard_snapshot(
        [_trace()], audit_log, task_store, memory_store, graph_store,
        tenant_id="t1", user_id="alice", groundedness=0.9, regression_passed=True,
    )

    assert snapshot.today.agent_runs == 1
    assert snapshot.memory.memories == 0
    assert snapshot.ai_health.regression_status == "PASS"
