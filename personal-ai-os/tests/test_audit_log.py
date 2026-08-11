from app.actions.audit_log import AuditLog
from app.actions.models import ActionClass, ActionProposal, ApprovalStatus, AuditRecord
from app.db.connection import get_connection


def _log() -> AuditLog:
    return AuditLog(get_connection(":memory:"))


def _proposal(action_id="a1") -> ActionProposal:
    return ActionProposal(action_id=action_id, action_class=ActionClass.ACT, tool_name="send_email", description="send", args={})


def test_record_and_get():
    log = _log()
    log.record(AuditRecord(action_id="a1", proposal=_proposal(), approval_status=ApprovalStatus.PENDING))

    record = log.get("a1")

    assert record is not None
    assert record.approval_status == ApprovalStatus.PENDING


def test_get_missing_returns_none():
    log = _log()

    assert log.get("does-not-exist") is None


def test_list_all_returns_all_records():
    log = _log()
    log.record(AuditRecord(action_id="a1", proposal=_proposal("a1"), approval_status=ApprovalStatus.PENDING))
    log.record(AuditRecord(action_id="a2", proposal=_proposal("a2"), approval_status=ApprovalStatus.APPROVED))

    records = log.list_all()

    assert len(records) == 2


def test_list_pending_approval_filters_correctly():
    log = _log()
    log.record(AuditRecord(action_id="a1", proposal=_proposal("a1"), approval_status=ApprovalStatus.PENDING))
    log.record(AuditRecord(action_id="a2", proposal=_proposal("a2"), approval_status=ApprovalStatus.APPROVED))

    pending = log.list_pending_approval()

    assert len(pending) == 1
    assert pending[0].action_id == "a1"


def test_record_upserts_by_action_id():
    log = _log()
    log.record(AuditRecord(action_id="a1", proposal=_proposal("a1"), approval_status=ApprovalStatus.PENDING))
    log.record(AuditRecord(action_id="a1", proposal=_proposal("a1"), approval_status=ApprovalStatus.APPROVED, approved_by="alice"))

    record = log.get("a1")

    assert record.approval_status == ApprovalStatus.APPROVED
    assert len(log.list_all()) == 1
