"""Generates REAL undo/recovery examples for the dashboard, found missing
while investigating "Human-in-the-Loop AI" (criterion: "understand undo/
recovery"). Every real tool before this batch was read-only -- there was
no writing action anywhere to attach a real undo to. This script proves
the new Tool.undo()/PolicyEngine.undo_action() mechanism end to end for
all 6 new real writing tools (app/tools/writing_tools.py): propose ->
(approve if ACT) -> execute -> undo, with a real before/after check each
time (the written thing genuinely exists, then genuinely doesn't).

modify_github is NOT simulated: it genuinely pushes a branch with a real
commit to the real chinmays188/linkedin-mcp-server repo over SSH, then
genuinely deletes that branch for real. Every other tool operates on a
real in-memory store/client (SQLite stores are real and persistent;
CalendarClient/EmailClient are intentionally simulated in-memory, same
fidelity as their existing read methods -- no OAuth/SMTP configured).

Usage:
    PYTHONPATH=. python scripts/generate_undo_examples.py
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.actions.audit_log import AuditLog
from app.actions.classification import ActionClassifier
from app.actions.policy_engine import ApprovalPending, PolicyEngine
from app.db.connection import get_connection
from app.domains.cross_domain.goal_store import GoalNotFoundError, GoalStore
from app.domains.router import Domain
from app.integrations.calendar_client import CalendarClient
from app.integrations.email_client import EmailClient
from app.integrations.github_git_write_client import GitHubGitWriteClient
from app.memory.models import MemoryType
from app.memory.persistent_store import PersistentMemoryStore
from app.platform.sandbox import SandboxedToolExecutor, SandboxLimits
from app.proactive.commitments import CommitmentNotFoundError, CommitmentOwner, CommitmentStore
from app.safety.permissions import PermissionChecker
from app.tools.writing_tools import (
    CreateCalendarEventTool,
    CreateCommitmentTool,
    CreateGoalTool,
    ModifyGithubTool,
    SendEmailTool,
    WriteMemoryTool,
)

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "undo_examples.json"

GITHUB_SSH_REMOTE = "git@github.com:chinmays188/linkedin-mcp-server.git"


def demo_create_goal(db_path: str) -> dict:
    tool = CreateGoalTool(db_path)
    store = GoalStore(get_connection(db_path))

    engine = PolicyEngine(
        ActionClassifier(), PermissionChecker({"write:goals"}),
        AuditLog(get_connection(":memory:")), {"create_goal": tool},
    )
    args_dict = {"owner_id": "demo_user", "title": "Learn Kubernetes", "domain": Domain.LEARNING.value}
    try:
        result = engine.propose_and_execute("create_goal", args_dict, "Create a goal via create_goal tool")
    except ApprovalPending as exc:
        result = engine.resume_after_approval(exc.action_id, approved=True, approved_by="demo_user")

    exists_after_create = True
    try:
        store.get(result)
    except GoalNotFoundError:
        exists_after_create = False

    action_id = engine._audit.list_all()[0].action_id
    undo_result = engine.undo_action(action_id, undone_by="demo_user")

    exists_after_undo = True
    try:
        store.get(result)
    except GoalNotFoundError:
        exists_after_undo = False

    return {
        "tool": "create_goal", "description": "Create a new tracked goal", "args": args_dict,
        "execution_result": result, "exists_after_create": exists_after_create,
        "undo_result": undo_result, "exists_after_undo": exists_after_undo,
    }


def demo_create_commitment(db_path: str) -> dict:
    tool = CreateCommitmentTool(db_path)
    store = CommitmentStore(get_connection(db_path))
    engine = PolicyEngine(
        ActionClassifier(), PermissionChecker({"write:commitments"}),
        AuditLog(get_connection(":memory:")), {"create_commitment": tool},
    )
    args_dict = {"owner_id": "demo_user", "description": "Send follow-up email", "owner": CommitmentOwner.USER.value}
    try:
        result = engine.propose_and_execute("create_commitment", args_dict, "Create a commitment")
    except ApprovalPending as exc:
        result = engine.resume_after_approval(exc.action_id, approved=True, approved_by="demo_user")

    exists_after_create = True
    try:
        store.get(result)
    except CommitmentNotFoundError:
        exists_after_create = False

    action_id = engine._audit.list_all()[0].action_id
    undo_result = engine.undo_action(action_id, undone_by="demo_user")

    exists_after_undo = True
    try:
        store.get(result)
        exists_after_undo = True
    except CommitmentNotFoundError:
        exists_after_undo = False

    return {
        "tool": "create_commitment", "description": "Record a new commitment", "args": args_dict,
        "execution_result": result, "exists_after_create": exists_after_create,
        "undo_result": undo_result, "exists_after_undo": exists_after_undo,
    }


def demo_write_memory(db_path: str) -> dict:
    tool = WriteMemoryTool(db_path)
    store = PersistentMemoryStore(get_connection(db_path))
    engine = PolicyEngine(
        ActionClassifier(), PermissionChecker({"write:memory"}),
        AuditLog(get_connection(":memory:")), {"write_memory": tool},
    )
    args_dict = {"tenant_id": "demo_tenant", "user_id": "demo_user", "type": MemoryType.PREFERENCE.value, "content": "Prefers concise answers"}
    try:
        result = engine.propose_and_execute("write_memory", args_dict, "Save a preference")
    except ApprovalPending as exc:
        result = engine.resume_after_approval(exc.action_id, approved=True, approved_by="demo_user")

    exists_after_create = store.get("demo_tenant", "demo_user", result) is not None

    action_id = engine._audit.list_all()[0].action_id
    undo_result = engine.undo_action(action_id, undone_by="demo_user")

    exists_after_undo = store.get("demo_tenant", "demo_user", result) is not None

    return {
        "tool": "write_memory", "description": "Save a piece of long-term memory", "args": args_dict,
        "execution_result": result, "exists_after_create": exists_after_create,
        "undo_result": undo_result, "exists_after_undo": exists_after_undo,
    }


def demo_create_calendar_event(calendar_file: str) -> dict:
    client = CalendarClient(file_path=calendar_file)
    tool = CreateCalendarEventTool(client)
    engine = PolicyEngine(
        ActionClassifier(), PermissionChecker({"write:calendar"}),
        AuditLog(get_connection(":memory:")), {"create_calendar_event": tool},
    )
    start = datetime(2026, 2, 1, 9, tzinfo=timezone.utc)
    end = datetime(2026, 2, 1, 10, tzinfo=timezone.utc)
    args_dict = {"title": "Team Sync", "start": start.isoformat(), "end": end.isoformat()}

    pending_action_id = None
    try:
        result = engine.propose_and_execute("create_calendar_event", args_dict, "Create a calendar event")
    except ApprovalPending as exc:
        pending_action_id = exc.action_id
        result = engine.resume_after_approval(pending_action_id, approved=True, approved_by="demo_user")

    exists_after_create = len(client.get_events(start)) == 1

    action_id = engine._audit.list_all()[0].action_id
    undo_result = engine.undo_action(action_id, undone_by="demo_user")

    exists_after_undo = len(client.get_events(start)) == 1

    return {
        "tool": "create_calendar_event", "description": "Create a new calendar event", "args": args_dict,
        "execution_result": result, "went_through_approval": pending_action_id is not None,
        "exists_after_create": exists_after_create,
        "undo_result": undo_result, "exists_after_undo": exists_after_undo,
    }


def demo_send_email(email_file: str) -> dict:
    client = EmailClient(file_path=email_file)
    tool = SendEmailTool(client)
    engine = PolicyEngine(
        ActionClassifier(), PermissionChecker({"write:email"}),
        AuditLog(get_connection(":memory:")), {"send_email": tool},
    )
    args_dict = {"sender": "demo_user@example.com", "subject": "Follow-up", "body": "Just checking in."}

    pending_action_id = None
    try:
        result = engine.propose_and_execute("send_email", args_dict, "Send a follow-up email")
    except ApprovalPending as exc:
        pending_action_id = exc.action_id
        result = engine.resume_after_approval(pending_action_id, approved=True, approved_by="demo_user")

    now = datetime.now(timezone.utc)
    exists_after_create = any(e.email_id == result for e in client.get_emails(now.replace(hour=0), now.replace(hour=23)))

    action_id = engine._audit.list_all()[0].action_id
    undo_result = engine.undo_action(action_id, undone_by="demo_user")

    exists_after_undo = any(e.email_id == result for e in client.get_emails(now.replace(hour=0), now.replace(hour=23)))

    return {
        "tool": "send_email", "description": "Send an email", "args": args_dict,
        "execution_result": result, "went_through_approval": pending_action_id is not None,
        "exists_after_create": exists_after_create,
        "undo_result": undo_result, "exists_after_undo": exists_after_undo,
    }


def demo_modify_github() -> dict:
    """The one NOT simulated: a real, live push + delete against the real
    chinmays188/linkedin-mcp-server repo over SSH."""
    import uuid

    client = GitHubGitWriteClient(GITHUB_SSH_REMOTE)
    tool = ModifyGithubTool(client)
    # Real finding from running this live: the default HIGH-risk sandbox
    # timeout (3s) is tuned for in-process calls and correctly killed a
    # real git clone+push over the network, which genuinely needs more
    # real wall-clock time. A longer, tool-appropriate override -- not a
    # change to the shared HIGH-risk default other tools still use.
    from app.actions.models import RiskLevel

    sandbox = SandboxedToolExecutor({RiskLevel.HIGH: SandboxLimits(timeout_seconds=30.0, memory_limit_mb=256)})
    engine = PolicyEngine(
        ActionClassifier(), PermissionChecker({"write:github"}),
        AuditLog(get_connection(":memory:")), {"modify_github": tool}, sandbox=sandbox,
    )
    branch_name = f"hitl-undo-demo-{uuid.uuid4().hex[:8]}"
    args_dict = {
        "branch_name": branch_name,
        "commit_message": "Real Human-in-the-Loop undo demo (will be deleted)",
    }

    pending_action_id = None
    try:
        result = engine.propose_and_execute("modify_github", args_dict, "Push a demo branch")
    except ApprovalPending as exc:
        pending_action_id = exc.action_id
        result = engine.resume_after_approval(pending_action_id, approved=True, approved_by="demo_user")

    import time

    import httpx

    check_url = f"https://api.github.com/repos/chinmays188/linkedin-mcp-server/branches/{branch_name}"
    exists_after_create = httpx.get(check_url, timeout=10).status_code == 200

    action_id = engine._audit.list_all()[0].action_id
    undo_result = engine.undo_action(action_id, undone_by="demo_user")

    # Real finding: GitHub's branch API can briefly still return 200 right
    # after a real delete (server-side propagation delay, confirmed by
    # re-checking moments later and seeing a real 404) -- a short real
    # retry here avoids recording a false "still exists" from a timing
    # artifact, not from the undo itself failing.
    exists_after_undo = True
    for _ in range(5):
        time.sleep(2)
        if httpx.get(check_url, timeout=10).status_code == 404:
            exists_after_undo = False
            break

    return {
        "tool": "modify_github", "description": "Push a new branch with a commit (REAL, live, not simulated)",
        "args": args_dict, "execution_result": result, "went_through_approval": pending_action_id is not None,
        "exists_after_create": exists_after_create,
        "undo_result": undo_result, "exists_after_undo": exists_after_undo,
        "repo": "chinmays188/linkedin-mcp-server",
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        examples = [
            demo_create_goal(str(tmp / "goals.db")),
            demo_create_commitment(str(tmp / "commitments.db")),
            demo_write_memory(str(tmp / "memory.db")),
            demo_create_calendar_event(str(tmp / "calendar.json")),
            demo_send_email(str(tmp / "email.json")),
            demo_modify_github(),
        ]
    for ex in examples:
        print(f"[{ex['tool']}] exists_after_create={ex['exists_after_create']} -> undo -> exists_after_undo={ex['exists_after_undo']}")

    OUT_PATH.write_text(json.dumps({"examples": examples}, indent=2))
    print(f"\nWrote real undo examples to {OUT_PATH}")


if __name__ == "__main__":
    main()
