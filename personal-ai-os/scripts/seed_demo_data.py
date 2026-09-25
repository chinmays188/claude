"""Seeds the real SQLite stores with fabricated, realistic demo data so the
Dashboard (Milestone: Dashboard UI) has something to display immediately,
without needing hours of real usage first.

Consistent with this project's synthetic-data-only convention for domain
workflows (Phase 3): every name, achievement, portfolio, and conversation
here is fabricated for demo purposes, not real personal/financial data.

Usage:
    PYTHONPATH=. python scripts/seed_demo_data.py [--db path/to/db]

Idempotent-ish: uses fixed ids where practical so re-running updates records
in place rather than duplicating them (stores use INSERT OR REPLACE keyed by
their own id fields).
"""

import argparse
from datetime import date, datetime, timedelta, timezone

from app.actions.audit_log import AuditLog
from app.actions.models import ActionClass, ActionProposal, ApprovalStatus, AuditRecord, RiskLevel
from app.dashboard_ui.example_traces import seed_example_traces
from app.dashboard_ui.user_learning_goals import seed_learning_capability_goals
from app.db.connection import get_connection
from app.domains.cross_domain.goal_store import GoalStore
from app.graph.models import Decision, GraphNode, NodeType
from app.graph.store import GraphStore
from app.memory.models import MemoryRecord, MemoryType
from app.memory.persistent_store import PersistentMemoryStore
from app.observability.trace_store import TraceStore
from app.proactive.commitments import Commitment, CommitmentOwner, CommitmentStatus, CommitmentStore
from app.proactive.outcome_tracking import Outcome, OutcomeStatus, OutcomeStore
from app.tasks.models import LongRunningTask, TaskState
from app.tasks.store import TaskStore

TENANT_ID = "demo_tenant"
USER_ID = "demo_user"
NOW = datetime.now(timezone.utc)
TODAY = date.today()


def seed_memories(store: PersistentMemoryStore) -> None:
    memories = [
        ("mem_goal_1", MemoryType.GOAL, "Wants to become an AI PM within 12 months.", 0.9),
        ("mem_pref_1", MemoryType.PREFERENCE, "Prefers concise, bullet-point explanations.", 0.6),
        ("mem_decision_1", MemoryType.DECISION, "Chose RAG over fine-tuning for the personal AI OS project.", 0.8),
        ("mem_learning_1", MemoryType.LEARNING, "Currently studying Kubernetes fundamentals.", 0.7),
        ("mem_project_1", MemoryType.PROJECT, "Building a Personal AI Operating System across 5 phases.", 0.85),
    ]
    for memory_id, mem_type, content, importance in memories:
        store.write(
            MemoryRecord(
                memory_id=memory_id, tenant_id=TENANT_ID, user_id=USER_ID, type=mem_type,
                content=content, source="demo_seed", created_at=NOW, updated_at=NOW,
                importance=importance, user_confirmed=True,
            )
        )


# The 4 fabricated demo goals that used to live here (one per domain: a
# fake career goal, a fake Kubernetes goal, a fake PM goal, a fake finance
# goal) were removed per the user's explicit choice, replaced by their real
# personal learning goals -- see app/dashboard_ui/user_learning_goals.py's
# seed_learning_capability_goals(), kept in its own module since that
# content is real, not fabricated demo data like the rest of this file.
# Real personal domain goals (Career/PM/Finance/Learning, distinct from
# that capability-tracking list) were discussed but not yet specified --
# a separate, later step.


def seed_graph(store: GraphStore) -> None:
    project_node = GraphNode(node_id="proj_personal_ai_os", owner_id=USER_ID, type=NodeType.PROJECT, label="Personal AI OS")
    store.add_node(project_node)
    store.add_node(GraphNode(owner_id=USER_ID, type=NodeType.ACHIEVEMENT, label="Shipped self-serve refund flow"))

    decisions = [
        Decision(
            owner_id=USER_ID, decision="Use RAG for spec Q&A", date=date(2026, 8, 1),
            context="The project's own spec doc changes frequently as milestones are added.",
            reason="RAG stays fresh without retraining and provides citations.",
            alternatives=["fine-tuning", "in-context learning"], chosen_option="RAG",
            expected_outcome="Accurate, up-to-date answers with citations.",
            actual_outcome="Worked well across all 5 phases.",
            related_project=project_node.node_id,
        ),
        Decision(
            owner_id=USER_ID, decision="Skip building a UI dashboard until Phase 5 was complete", date=date(2026, 8, 12),
            context="Multiple dashboard milestones across Phases 2-4 all specified data-layer-only.",
            reason="Avoid building UI against a data model that was still evolving milestone to milestone.",
            chosen_option="Data layer only, revisit UI after Phase 5",
            expected_outcome="A stable, tested data layer to build a real dashboard on top of later.",
            actual_outcome="Confirmed correct — the dashboard MVP now reuses that data layer directly.",
        ),
    ]
    for decision in decisions:
        store.add_decision(decision)
        # get_memory_summary() (Phase 2's dashboard) counts NodeType.DECISION
        # graph *nodes*, a separate, lighter-weight concept from the detailed
        # `decisions` table row above -- both are seeded so every dashboard
        # view that reads either representation shows real data.
        store.add_node(GraphNode(owner_id=USER_ID, type=NodeType.DECISION, label=decision.decision))


def seed_tasks(store: TaskStore) -> None:
    task = LongRunningTask(owner=USER_ID, description="Research top 10 AI PM companies for applications.")
    store.create(task)
    store.transition(task.task_id, TaskState.PLANNING)
    store.transition(task.task_id, TaskState.RUNNING)
    store.transition(task.task_id, TaskState.EVALUATING)
    store.transition(
        task.task_id, TaskState.COMPLETED,
        result="Identified 10 companies with active AI PM openings; 4 have roles matching target seniority.",
    )


def seed_audit_log(store: AuditLog) -> None:
    read_proposal = ActionProposal(
        action_class=ActionClass.READ, tool_name="github_activity",
        description="Check this week's GitHub activity.", args={}, risk_level=RiskLevel.LOW,
    )
    store.record(
        AuditRecord(
            action_id=read_proposal.action_id, proposal=read_proposal, approval_status=ApprovalStatus.AUTO_APPROVED,
            executed=True, execution_result="3 PRs merged this week.", verified=True,
            verification_note="Execution produced a non-empty result.",
        )
    )

    pending_proposal = ActionProposal(
        action_class=ActionClass.ACT, tool_name="send_email",
        description="Draft a follow-up email to a hiring manager.", args={}, risk_level=RiskLevel.HIGH,
    )
    store.record(
        AuditRecord(action_id=pending_proposal.action_id, proposal=pending_proposal, approval_status=ApprovalStatus.PENDING)
    )


def seed_commitments(store: CommitmentStore) -> None:
    store.save(
        Commitment(
            commitment_id="commit_1", owner_id=USER_ID, description="Send updated resume to recruiter",
            owner=CommitmentOwner.USER, due_date=TODAY - timedelta(days=2), status=CommitmentStatus.OPEN,
            source_text="I'll send my updated resume by end of week.",
        )
    )
    store.save(
        Commitment(
            commitment_id="commit_2", owner_id=USER_ID, description="Hiring manager to share interview feedback",
            owner=CommitmentOwner.OTHER_PARTY, due_date=TODAY + timedelta(days=3), status=CommitmentStatus.OPEN,
            source_text="They said they'd share feedback within a week of the interview.",
        )
    )


def seed_outcomes(store: OutcomeStore) -> None:
    store.record(
        Outcome(outcome_id="outcome_1", action_id="pending_action_1", owner_id=USER_ID, expected_result="Stakeholder replies to follow-up email")
    )
    resolved = Outcome(outcome_id="outcome_2", action_id="pending_action_2", owner_id=USER_ID, expected_result="Refund automation PRD gets approved")
    store.record(resolved)
    store.resolve(resolved.outcome_id, OutcomeStatus.ACHIEVED, "PRD approved after Critic Agent review; moved to sprint planning.")


def seed_all(conn) -> None:
    """Seed every store against an already-open connection.

    Factored out from main() so dashboard_app.py can call this directly on
    first load (e.g. on Streamlit Community Cloud, where there's no separate
    manual step to run this script before the app starts).
    """
    seed_memories(PersistentMemoryStore(conn))
    seed_learning_capability_goals(GoalStore(conn))
    seed_graph(GraphStore(conn))
    seed_tasks(TaskStore(conn))
    seed_audit_log(AuditLog(conn))
    seed_commitments(CommitmentStore(conn))
    seed_outcomes(OutcomeStore(conn))
    seed_example_traces(TraceStore(conn))


def main(db_path: str) -> None:
    conn = get_connection(db_path)
    seed_all(conn)
    print(f"Seeded demo data into {db_path} for tenant='{TENANT_ID}', user='{USER_ID}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/personal_ai.db", help="Path to the SQLite database file.")
    args = parser.parse_args()
    main(args.db)
