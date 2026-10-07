import pytest
from pydantic import BaseModel

from app.actions.audit_log import AuditLog
from app.actions.classification import ActionClassifier
from app.actions.models import ActionClass, ApprovalStatus
from app.actions.policy_engine import ApprovalPending, PolicyEngine
from app.db.connection import get_connection
from app.safety.permissions import PermissionChecker, PermissionDeniedError
from app.tools.base import Tool, UndoNotSupportedError
from app.tools.calculator import CalculatorTool


class SendArgs(BaseModel):
    to: str
    message: str


class FakeSendEmailTool(Tool):
    name = "send_email"
    description = "sends an email"
    args_schema = SendArgs
    permissions = ["write:email"]

    def run(self, args: SendArgs) -> str:
        return f"Sent to {args.to}: {args.message}"


class FakeUndoableSendEmailTool(FakeSendEmailTool):
    undoable = True

    def __init__(self):
        self.undone_args = None

    def undo(self, args: SendArgs, result: str) -> str:
        self.undone_args = args
        return f"Recalled: {result}"


class FakeToolWithCustomVerify(FakeSendEmailTool):
    def __init__(self, verify_result: tuple[bool, str]):
        self._verify_result = verify_result

    def verify(self, args: SendArgs, result: str) -> tuple[bool, str]:
        return self._verify_result


def _engine(granted_permissions: set[str], overrides=None) -> PolicyEngine:
    classifier = ActionClassifier(overrides=overrides)
    permission_checker = PermissionChecker(granted_permissions)
    audit_log = AuditLog(get_connection(":memory:"))
    tools = {"calculator": CalculatorTool(), "send_email": FakeSendEmailTool()}
    return PolicyEngine(classifier, permission_checker, audit_log, tools)


def test_read_action_executes_immediately_no_approval_needed():
    engine = _engine(granted_permissions={"compute:local"})

    result = engine.propose_and_execute("calculator", {"expression": "2+2"}, "compute")

    assert result == "4"


def test_read_action_is_still_audited():
    classifier = ActionClassifier()
    permission_checker = PermissionChecker({"compute:local"})
    audit_log = AuditLog(get_connection(":memory:"))
    engine = PolicyEngine(classifier, permission_checker, audit_log, {"calculator": CalculatorTool()})

    engine.propose_and_execute("calculator", {"expression": "2+2"}, "compute")

    records = audit_log.list_all()
    assert len(records) == 1
    assert records[0].approval_status == ApprovalStatus.AUTO_APPROVED
    assert records[0].executed is True


def test_act_action_raises_approval_pending():
    engine = _engine(granted_permissions={"write:email"})

    with pytest.raises(ApprovalPending) as exc_info:
        engine.propose_and_execute("send_email", {"to": "a@b.com", "message": "hi"}, "notify")

    assert exc_info.value.action_id


def test_approved_action_executes_on_resume():
    engine = _engine(granted_permissions={"write:email"})

    try:
        engine.propose_and_execute("send_email", {"to": "a@b.com", "message": "hi"}, "notify")
    except ApprovalPending as e:
        action_id = e.action_id

    result = engine.resume_after_approval(action_id, approved=True, approved_by="alice")

    assert "Sent to a@b.com" in result


def test_rejected_action_never_executes():
    engine = _engine(granted_permissions={"write:email"})

    try:
        engine.propose_and_execute("send_email", {"to": "a@b.com", "message": "hi"}, "notify")
    except ApprovalPending as e:
        action_id = e.action_id

    result = engine.resume_after_approval(action_id, approved=False, approved_by="alice")

    assert "rejected" in result.lower()


def test_permission_denied_even_after_approval():
    engine = _engine(granted_permissions=set())  # no write:email granted

    try:
        engine.propose_and_execute("send_email", {"to": "a@b.com", "message": "hi"}, "notify")
    except ApprovalPending as e:
        action_id = e.action_id

    with pytest.raises(PermissionDeniedError):
        engine.resume_after_approval(action_id, approved=True, approved_by="alice")


def test_resuming_unknown_action_id_raises():
    engine = _engine(granted_permissions=set())

    with pytest.raises(ValueError):
        engine.resume_after_approval("does-not-exist", approved=True, approved_by="alice")


def test_resuming_already_resolved_action_raises():
    engine = _engine(granted_permissions={"write:email"})

    try:
        engine.propose_and_execute("send_email", {"to": "a@b.com", "message": "hi"}, "notify")
    except ApprovalPending as e:
        action_id = e.action_id

    engine.resume_after_approval(action_id, approved=True, approved_by="alice")

    with pytest.raises(ValueError):
        engine.resume_after_approval(action_id, approved=True, approved_by="alice")


def test_full_pipeline_produces_verified_audit_record():
    classifier = ActionClassifier()
    permission_checker = PermissionChecker({"write:email"})
    audit_log = AuditLog(get_connection(":memory:"))
    engine = PolicyEngine(classifier, permission_checker, audit_log, {"send_email": FakeSendEmailTool()})

    try:
        engine.propose_and_execute("send_email", {"to": "a@b.com", "message": "hi"}, "notify")
    except ApprovalPending as e:
        action_id = e.action_id

    engine.resume_after_approval(action_id, approved=True, approved_by="alice")

    record = audit_log.get(action_id)
    assert record.executed is True
    assert record.verified is True
    assert record.approved_by == "alice"


def test_undo_action_reverses_an_executed_undoable_action():
    classifier = ActionClassifier()
    permission_checker = PermissionChecker({"write:email"})
    audit_log = AuditLog(get_connection(":memory:"))
    tool = FakeUndoableSendEmailTool()
    engine = PolicyEngine(classifier, permission_checker, audit_log, {"send_email": tool})

    try:
        engine.propose_and_execute("send_email", {"to": "a@b.com", "message": "hi"}, "notify")
    except ApprovalPending as e:
        action_id = e.action_id
    engine.resume_after_approval(action_id, approved=True, approved_by="alice")

    result = engine.undo_action(action_id, undone_by="alice")

    assert "Recalled" in result
    assert tool.undone_args.to == "a@b.com"
    record = audit_log.get(action_id)
    assert record.undone is True
    assert record.undo_result == result
    assert record.undone_by == "alice"


def test_undo_action_raises_when_tool_does_not_support_it():
    engine = _engine(granted_permissions={"write:email"})  # FakeSendEmailTool: undoable=False

    try:
        engine.propose_and_execute("send_email", {"to": "a@b.com", "message": "hi"}, "notify")
    except ApprovalPending as e:
        action_id = e.action_id
    engine.resume_after_approval(action_id, approved=True, approved_by="alice")

    with pytest.raises(UndoNotSupportedError):
        engine.undo_action(action_id, undone_by="alice")


def test_undo_action_raises_for_unexecuted_action():
    engine = _engine(granted_permissions={"write:email"})

    try:
        engine.propose_and_execute("send_email", {"to": "a@b.com", "message": "hi"}, "notify")
    except ApprovalPending as e:
        action_id = e.action_id

    with pytest.raises(ValueError):
        engine.undo_action(action_id, undone_by="alice")


def test_undo_action_raises_when_already_undone():
    classifier = ActionClassifier()
    permission_checker = PermissionChecker({"write:email"})
    audit_log = AuditLog(get_connection(":memory:"))
    tool = FakeUndoableSendEmailTool()
    engine = PolicyEngine(classifier, permission_checker, audit_log, {"send_email": tool})

    try:
        engine.propose_and_execute("send_email", {"to": "a@b.com", "message": "hi"}, "notify")
    except ApprovalPending as e:
        action_id = e.action_id
    engine.resume_after_approval(action_id, approved=True, approved_by="alice")
    engine.undo_action(action_id, undone_by="alice")

    with pytest.raises(ValueError):
        engine.undo_action(action_id, undone_by="alice")


def test_undo_action_raises_for_unknown_action_id():
    engine = _engine(granted_permissions=set())

    with pytest.raises(ValueError):
        engine.undo_action("does-not-exist", undone_by="alice")


def test_verify_falls_back_to_generic_check_when_tool_has_none():
    classifier = ActionClassifier()
    permission_checker = PermissionChecker({"write:email"})
    audit_log = AuditLog(get_connection(":memory:"))
    engine = PolicyEngine(classifier, permission_checker, audit_log, {"send_email": FakeSendEmailTool()})

    try:
        engine.propose_and_execute("send_email", {"to": "a@b.com", "message": "hi"}, "notify")
    except ApprovalPending as e:
        action_id = e.action_id
    engine.resume_after_approval(action_id, approved=True, approved_by="alice")

    record = audit_log.get(action_id)
    assert record.verified is True  # generic non-empty-result check, FakeSendEmailTool has no verify()
    assert "non-empty result" in record.verification_note


def test_verify_uses_tool_specific_check_when_present():
    classifier = ActionClassifier()
    permission_checker = PermissionChecker({"write:email"})
    audit_log = AuditLog(get_connection(":memory:"))
    tool = FakeToolWithCustomVerify(verify_result=(False, "custom check failed"))
    engine = PolicyEngine(classifier, permission_checker, audit_log, {"send_email": tool})

    try:
        engine.propose_and_execute("send_email", {"to": "a@b.com", "message": "hi"}, "notify")
    except ApprovalPending as e:
        action_id = e.action_id
    engine.resume_after_approval(action_id, approved=True, approved_by="alice")

    record = audit_log.get(action_id)
    assert record.verified is False  # tool-specific check wins even though the result was non-empty
    assert record.verification_note == "custom check failed"
