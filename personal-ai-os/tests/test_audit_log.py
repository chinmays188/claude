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


def test_undone_fields_round_trip():
    log = _log()
    log.record(
        AuditRecord(
            action_id="a1", proposal=_proposal("a1"), approval_status=ApprovalStatus.UNDONE,
            executed=True, undone=True, undo_result="Deleted goal 'g1'.", undone_by="alice",
        )
    )

    record = log.get("a1")

    assert record.undone is True
    assert record.undo_result == "Deleted goal 'g1'."
    assert record.undone_by == "alice"


def test_list_executed_not_undone_filters_correctly():
    log = _log()
    log.record(AuditRecord(action_id="a1", proposal=_proposal("a1"), approval_status=ApprovalStatus.APPROVED, executed=True))
    log.record(AuditRecord(action_id="a2", proposal=_proposal("a2"), approval_status=ApprovalStatus.APPROVED, executed=True, undone=True))
    log.record(AuditRecord(action_id="a3", proposal=_proposal("a3"), approval_status=ApprovalStatus.PENDING, executed=False))
    log.record(AuditRecord(action_id="a4", proposal=_proposal("a4"), approval_status=ApprovalStatus.REJECTED, executed=False))

    candidates = log.list_executed_not_undone()

    assert {r.action_id for r in candidates} == {"a1"}


def test_migration_adds_undo_columns_to_a_pre_existing_table():
    conn = get_connection(":memory:")
    # Simulate a real, already-existing audit_log table from before the
    # undo columns existed -- the exact real scenario found with
    # data/personal_ai.db (first real migration this project has needed).
    conn.executescript(
        """CREATE TABLE audit_log (
            action_id TEXT PRIMARY KEY, proposal_json TEXT NOT NULL, approval_status TEXT NOT NULL,
            approved_by TEXT, executed INTEGER NOT NULL, execution_result TEXT,
            verified INTEGER NOT NULL, verification_note TEXT, recorded_at TEXT NOT NULL
        );"""
    )
    conn.commit()

    log = AuditLog(conn)  # should migrate, not raise
    log.record(AuditRecord(action_id="a1", proposal=_proposal("a1"), approval_status=ApprovalStatus.PENDING))

    assert log.get("a1").undone is False
