import pytest
from pydantic import BaseModel

from app.actions.audit_log import AuditLog
from app.actions.classification import ActionClassifier
from app.actions.models import ActionClass, ApprovalStatus
from app.actions.policy_engine import ApprovalPending, PolicyEngine
from app.db.connection import get_connection
from app.safety.permissions import PermissionChecker, PermissionDeniedError
from app.tools.base import Tool
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
