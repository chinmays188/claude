"""Real writing (ACT-class) tools with real undo, built while investigating
"Human-in-the-Loop AI" (criterion: "understand undo/recovery"). Every
existing real Tool before this file was read-only (calculator, retrieve,
calendar_day, email_summary, github_activity, analyze_feedback/jd,
draft_prd) -- a real, deeper gap than the original "no undo mechanism"
framing: there was no WRITING action anywhere to attach undo to at all.

Each tool here genuinely writes something and genuinely reverses it via
Tool.undo() -- no simulated success, no silent no-op. CreateGoalTool/
CreateCommitmentTool/WriteMemoryTool operate on this project's own real
SQLite stores. CreateCalendarEventTool/SendEmailTool operate on their
real (but intentionally simulated, no OAuth/SMTP configured) in-memory
clients. ModifyGithubTool is the one exception that is NOT simulated --
it genuinely pushes to and deletes a branch on a real GitHub repo over
SSH (see app/integrations/github_git_write_client.py's docstring for why
git-over-SSH instead of the REST API).
"""

import sqlite3
from datetime import date, datetime, timezone
from uuid import uuid4

from pydantic import BaseModel

from app.db.connection import get_connection
from app.domains.cross_domain.goal_store import GoalStore
from app.domains.cross_domain.models import Goal, GoalStatus
from app.domains.router import Domain
from app.integrations.calendar_client import CalendarClient, CalendarEvent
from app.integrations.email_client import Email, EmailClient
from app.integrations.github_git_write_client import GitHubGitWriteClient
from app.memory.models import MemoryRecord, MemoryType
from app.memory.persistent_store import PersistentMemoryStore
from app.proactive.commitments import Commitment, CommitmentOwner, CommitmentStore
from app.tools.base import Tool


class _DbBackedTool(Tool):
    """Real, significant finding from wiring these tools into
    SandboxedToolExecutor: it pickles the whole Tool object to send into a
    spawned child process (app/platform/sandbox.py), and a live
    sqlite3.Connection can't be pickled (TypeError). Every tool before this
    batch was stateless, so the sandbox never had to face this. Fixed by
    storing a db_path (a plain string, picklable) instead of a live
    Connection, and opening a fresh connection per real call -- consistent
    with how this project already treats SQLite connections as cheap to
    open (every *Store class does the same per-process)."""

    def __init__(self, db_path: str):
        self._db_path = db_path

    def _connection(self) -> sqlite3.Connection:
        return get_connection(self._db_path)


class CreateGoalArgs(BaseModel):
    owner_id: str
    title: str
    domain: Domain
    description: str = ""


class CreateGoalTool(_DbBackedTool):
    name = "create_goal"
    description = "Create a new tracked goal for a user."
    args_schema = CreateGoalArgs
    permissions = ["write:goals"]
    undoable = True

    def run(self, args: CreateGoalArgs) -> str:
        goal = Goal(owner_id=args.owner_id, title=args.title, domain=args.domain, description=args.description)
        GoalStore(self._connection()).create(goal)
        return goal.goal_id

    def undo(self, args: CreateGoalArgs, result: str) -> str:
        goal_id = result
        GoalStore(self._connection()).delete(goal_id)
        return f"Deleted goal '{goal_id}'."


class CreateCommitmentArgs(BaseModel):
    owner_id: str
    description: str
    owner: CommitmentOwner = CommitmentOwner.USER
    due_date: date | None = None


class CreateCommitmentTool(_DbBackedTool):
    name = "create_commitment"
    description = "Record a new commitment to track and follow up on."
    args_schema = CreateCommitmentArgs
    permissions = ["write:commitments"]
    undoable = True

    def run(self, args: CreateCommitmentArgs) -> str:
        commitment = Commitment(
            owner_id=args.owner_id, description=args.description, owner=args.owner, due_date=args.due_date,
        )
        CommitmentStore(self._connection()).save(commitment)
        return commitment.commitment_id

    def undo(self, args: CreateCommitmentArgs, result: str) -> str:
        commitment_id = result
        CommitmentStore(self._connection()).delete(commitment_id)
        return f"Deleted commitment '{commitment_id}'."


class WriteMemoryArgs(BaseModel):
    tenant_id: str
    user_id: str
    type: MemoryType
    content: str
    importance: float = 0.5


class WriteMemoryTool(_DbBackedTool):
    name = "write_memory"
    description = "Save a piece of long-term personal memory."
    args_schema = WriteMemoryArgs
    permissions = ["write:memory"]
    undoable = True

    def run(self, args: WriteMemoryArgs) -> str:
        now = datetime.now(timezone.utc)
        record = MemoryRecord(
            memory_id=uuid4().hex, tenant_id=args.tenant_id, user_id=args.user_id,
            type=args.type, content=args.content, source="write_memory_tool",
            created_at=now, updated_at=now, importance=args.importance,
        )
        PersistentMemoryStore(self._connection()).write(record)
        return record.memory_id

    def undo(self, args: WriteMemoryArgs, result: str) -> str:
        memory_id = result
        PersistentMemoryStore(self._connection()).delete(args.tenant_id, args.user_id, memory_id)
        return f"Deleted memory '{memory_id}'."


class CreateCalendarEventArgs(BaseModel):
    title: str
    start: datetime
    end: datetime
    attendees: list[str] = []


class CreateCalendarEventTool(Tool):
    name = "create_calendar_event"
    description = "Create a new calendar event."
    args_schema = CreateCalendarEventArgs
    permissions = ["write:calendar"]
    undoable = True

    def __init__(self, client: CalendarClient):
        self._client = client

    def run(self, args: CreateCalendarEventArgs) -> str:
        event = CalendarEvent(
            event_id=uuid4().hex, title=args.title, start=args.start, end=args.end, attendees=args.attendees,
        )
        self._client.create_event(event)
        return event.event_id

    def undo(self, args: CreateCalendarEventArgs, result: str) -> str:
        event_id = result
        self._client.delete_event(event_id)
        return f"Deleted calendar event '{event_id}'."


class SendEmailArgs(BaseModel):
    sender: str
    subject: str
    body: str


class SendEmailTool(Tool):
    name = "send_email"
    description = "Send an email."
    args_schema = SendEmailArgs
    permissions = ["write:email"]
    undoable = True

    def __init__(self, client: EmailClient):
        self._client = client

    def run(self, args: SendEmailArgs) -> str:
        email = Email(
            email_id=uuid4().hex, sender=args.sender, subject=args.subject,
            body=args.body, received_at=datetime.now(timezone.utc),
        )
        self._client.send_email(email)
        return email.email_id

    def undo(self, args: SendEmailArgs, result: str) -> str:
        email_id = result
        self._client.recall_email(email_id)
        return f"Recalled email '{email_id}'."


class ModifyGithubArgs(BaseModel):
    branch_name: str
    commit_message: str
    file_content: str = "Created by ModifyGithubTool (Human-in-the-Loop AI undo demo).\n"


class ModifyGithubTool(Tool):
    """The one tool here that is NOT simulated -- genuinely pushes to and
    deletes a branch on a real GitHub repo over SSH. See
    github_git_write_client.py's docstring for the real constraint that
    shaped this (no GITHUB_TOKEN configured, so REST-based issue creation
    wasn't possible; SSH push access was confirmed live instead)."""

    name = "modify_github"
    description = "Push a new branch with a commit to a GitHub repo."
    args_schema = ModifyGithubArgs
    permissions = ["write:github"]
    undoable = True

    def __init__(self, client: GitHubGitWriteClient):
        self._client = client

    def run(self, args: ModifyGithubArgs) -> str:
        sha = self._client.push_branch_with_commit(args.branch_name, args.commit_message, args.file_content)
        return f"{args.branch_name}@{sha}"

    def undo(self, args: ModifyGithubArgs, result: str) -> str:
        self._client.delete_branch(args.branch_name)
        return f"Deleted real remote branch '{args.branch_name}'."
