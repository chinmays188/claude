from datetime import date, datetime, timezone

from pydantic import BaseModel

from app.actions.audit_log import AuditLog
from app.actions.models import ApprovalStatus
from app.graph.models import NodeType
from app.graph.store import GraphStore
from app.memory.models import MemoryType
from app.memory.persistent_store import PersistentMemoryStore
from app.observability.traces import Trace
from app.tasks.models import TaskState
from app.tasks.store import TaskStore


class TodaysActivity(BaseModel):
    """Section 38's exact 'Today's Activity' block."""

    agent_runs: int
    tasks_completed: int
    pending_approvals: int
    evaluation_score: float | None = None  # 0.0-1.0; None if no evals ran today
    avg_latency_ms: float | None = None


class MemorySummary(BaseModel):
    """Section 38's exact 'Memory' block."""

    memories: int
    decisions: int
    projects: int


class AiHealth(BaseModel):
    """Section 38's exact 'AI Health' block."""

    groundedness: float | None = None
    tool_success_rate: float | None = None
    retrieval_recall: float | None = None
    regression_status: str = "UNKNOWN"  # "PASS" | "FAIL" | "UNKNOWN"


class DashboardSnapshot(BaseModel):
    today: TodaysActivity
    memory: MemorySummary
    ai_health: AiHealth


def get_todays_activity(
    traces: list[Trace], audit_log: AuditLog, task_store: TaskStore, owner: str, today: date | None = None
) -> TodaysActivity:
    today = today or datetime.now(timezone.utc).date()
    today_traces = [t for t in traces]  # Trace has no wall-clock date field yet; caller pre-filters by day

    tasks = task_store.list_by_owner(owner)
    completed_today = sum(
        1 for t in tasks if t.state == TaskState.COMPLETED and t.updated_at.date() == today
    )

    pending = len(audit_log.list_pending_approval())

    successful = [t for t in today_traces if t.status == "success"]
    eval_score = len(successful) / len(today_traces) if today_traces else None
    avg_latency = sum(t.latency_ms for t in today_traces) / len(today_traces) if today_traces else None

    return TodaysActivity(
        agent_runs=len(today_traces),
        tasks_completed=completed_today,
        pending_approvals=pending,
        evaluation_score=eval_score,
        avg_latency_ms=avg_latency,
    )


def get_memory_summary(memory_store: PersistentMemoryStore, graph_store: GraphStore, tenant_id: str, user_id: str) -> MemorySummary:
    return MemorySummary(
        memories=memory_store.count(tenant_id, user_id),
        decisions=len(graph_store.nodes_by_type(user_id, NodeType.DECISION)),
        projects=len(graph_store.nodes_by_type(user_id, NodeType.PROJECT)),
    )


def get_ai_health(
    groundedness: float | None = None,
    tool_success_rate: float | None = None,
    retrieval_recall: float | None = None,
    regression_passed: bool | None = None,
) -> AiHealth:
    """Assembles Section 38's 'AI Health' block from whatever eval results the
    caller has on hand (Milestone 8's grounding eval, Milestone 11's regression
    report, etc.) — this function doesn't run evaluations itself, it just shapes
    already-computed results into the dashboard's schema."""
    status = "UNKNOWN"
    if regression_passed is True:
        status = "PASS"
    elif regression_passed is False:
        status = "FAIL"

    return AiHealth(
        groundedness=groundedness, tool_success_rate=tool_success_rate,
        retrieval_recall=retrieval_recall, regression_status=status,
    )


def get_dashboard_snapshot(
    traces: list[Trace], audit_log: AuditLog, task_store: TaskStore,
    memory_store: PersistentMemoryStore, graph_store: GraphStore,
    tenant_id: str, user_id: str,
    groundedness: float | None = None, tool_success_rate: float | None = None,
    retrieval_recall: float | None = None, regression_passed: bool | None = None,
) -> DashboardSnapshot:
    return DashboardSnapshot(
        today=get_todays_activity(traces, audit_log, task_store, owner=user_id),
        memory=get_memory_summary(memory_store, graph_store, tenant_id, user_id),
        ai_health=get_ai_health(groundedness, tool_success_rate, retrieval_recall, regression_passed),
    )
