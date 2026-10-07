from datetime import datetime, timezone

import pytest

from app.db.connection import get_connection
from app.domains.cross_domain.goal_store import GoalNotFoundError, GoalStore
from app.domains.router import Domain
from app.integrations.calendar_client import CalendarClient
from app.integrations.email_client import EmailClient
from app.memory.models import MemoryType
from app.memory.persistent_store import PersistentMemoryStore
from app.proactive.commitments import CommitmentNotFoundError, CommitmentOwner, CommitmentStore
from app.tools.writing_tools import (
    CreateCalendarEventTool,
    CreateCommitmentTool,
    CreateGoalTool,
    ModifyGithubTool,
    SendEmailTool,
    WriteMemoryTool,
)


def _tmp_db_path(tmp_path) -> str:
    return str(tmp_path / "test.db")


def test_create_goal_tool_creates_and_undoes(tmp_path):
    db_path = _tmp_db_path(tmp_path)
    tool = CreateGoalTool(db_path)
    args = tool.validate_args({"owner_id": "alice", "title": "Learn Kubernetes", "domain": Domain.LEARNING.value})

    goal_id = tool.run(args)

    store = GoalStore(get_connection(db_path))
    assert store.get(goal_id).title == "Learn Kubernetes"

    verified, note = tool.verify(args, goal_id)
    assert verified is True

    tool.undo(args, goal_id)

    with pytest.raises(GoalNotFoundError):
        store.get(goal_id)


def test_create_goal_tool_verify_fails_after_undo(tmp_path):
    db_path = _tmp_db_path(tmp_path)
    tool = CreateGoalTool(db_path)
    args = tool.validate_args({"owner_id": "alice", "title": "Learn Kubernetes", "domain": Domain.LEARNING.value})
    goal_id = tool.run(args)
    tool.undo(args, goal_id)

    verified, note = tool.verify(args, goal_id)

    assert verified is False
    assert "not found" in note.lower()


def test_create_commitment_tool_creates_and_undoes(tmp_path):
    db_path = _tmp_db_path(tmp_path)
    tool = CreateCommitmentTool(db_path)
    args = tool.validate_args({"owner_id": "alice", "description": "Send report", "owner": CommitmentOwner.USER.value})

    commitment_id = tool.run(args)

    store = CommitmentStore(get_connection(db_path))
    assert store.get(commitment_id).description == "Send report"

    verified, note = tool.verify(args, commitment_id)
    assert verified is True

    tool.undo(args, commitment_id)

    with pytest.raises(CommitmentNotFoundError):
        store.get(commitment_id)


def test_write_memory_tool_writes_and_undoes(tmp_path):
    db_path = _tmp_db_path(tmp_path)
    tool = WriteMemoryTool(db_path)
    args = tool.validate_args({"tenant_id": "t1", "user_id": "u1", "type": MemoryType.PREFERENCE.value, "content": "likes dark mode"})

    memory_id = tool.run(args)

    store = PersistentMemoryStore(get_connection(db_path))
    assert store.get("t1", "u1", memory_id) is not None

    verified, note = tool.verify(args, memory_id)
    assert verified is True

    tool.undo(args, memory_id)

    assert store.get("t1", "u1", memory_id) is None


def test_create_calendar_event_tool_creates_and_undoes():
    client = CalendarClient()
    tool = CreateCalendarEventTool(client)
    start = datetime(2026, 1, 15, 9, tzinfo=timezone.utc)
    end = datetime(2026, 1, 15, 10, tzinfo=timezone.utc)
    args = tool.validate_args({"title": "Standup", "start": start.isoformat(), "end": end.isoformat()})

    event_id = tool.run(args)

    assert len(client.get_events(start)) == 1

    verified, note = tool.verify(args, event_id)
    assert verified is True

    tool.undo(args, event_id)

    assert len(client.get_events(start)) == 0


def test_send_email_tool_sends_and_undoes():
    client = EmailClient()
    tool = SendEmailTool(client)
    args = tool.validate_args({"sender": "me@x.com", "subject": "Hi", "body": "body"})

    email_id = tool.run(args)

    now = datetime.now(timezone.utc)
    assert any(e.email_id == email_id for e in client.get_emails(now.replace(hour=0), now.replace(hour=23)))

    verified, note = tool.verify(args, email_id)
    assert verified is True

    tool.undo(args, email_id)

    assert not any(e.email_id == email_id for e in client.get_emails(now.replace(hour=0), now.replace(hour=23)))


class _FakeGitHubGitWriteClient:
    def __init__(self):
        self.pushed = None
        self.deleted = None
        self._branches = set()

    def push_branch_with_commit(self, branch_name, commit_message, file_content):
        self.pushed = (branch_name, commit_message, file_content)
        self._branches.add(branch_name)
        return "fake-sha"

    def delete_branch(self, branch_name):
        self.deleted = branch_name
        self._branches.discard(branch_name)

    def branch_exists(self, branch_name):
        return branch_name in self._branches


def test_modify_github_tool_pushes_and_undoes():
    client = _FakeGitHubGitWriteClient()
    tool = ModifyGithubTool(client)
    args = tool.validate_args({"branch_name": "demo-branch", "commit_message": "demo commit"})

    result = tool.run(args)

    assert result == "demo-branch@fake-sha"
    assert client.pushed[0] == "demo-branch"

    verified, note = tool.verify(args, result)
    assert verified is True

    tool.undo(args, result)

    assert client.deleted == "demo-branch"

    verified, note = tool.verify(args, result)
    assert verified is False


def test_all_writing_tools_declare_undoable():
    assert CreateGoalTool.undoable is True
    assert CreateCommitmentTool.undoable is True
    assert WriteMemoryTool.undoable is True
    assert CreateCalendarEventTool.undoable is True
    assert SendEmailTool.undoable is True
    assert ModifyGithubTool.undoable is True
