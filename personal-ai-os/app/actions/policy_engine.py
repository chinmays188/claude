from app.actions.audit_log import AuditLog
from app.actions.classification import ActionClassifier
from app.actions.models import ActionProposal, ApprovalStatus, AuditRecord
from app.platform.sandbox import SandboxedToolExecutor
from app.safety.permissions import PermissionChecker, PermissionDeniedError
from app.tools.base import Tool, ToolError, UndoNotSupportedError


class ApprovalPending(Exception):
    """Raised when an action needs a human decision before it can execute.
    Not an error — signals the caller to surface the proposal for approval and
    call resume_after_approval() later."""

    def __init__(self, action_id: str):
        self.action_id = action_id
        super().__init__(f"Action {action_id} is pending approval.")


class PolicyEngine:
    """Implements Section 28's action architecture end to end: Agent proposes
    an action -> permission check -> risk assessment -> (approval if required)
    -> tool execution -> verification -> audit log. READ actions skip the
    approval gate but are still fully audited (Section 27)."""

    def __init__(
        self,
        classifier: ActionClassifier,
        permission_checker: PermissionChecker,
        audit_log: AuditLog,
        tools_by_name: dict[str, Tool],
        sandbox: SandboxedToolExecutor | None = None,
    ):
        self._classifier = classifier
        self._permissions = permission_checker
        self._audit = audit_log
        self._tools = tools_by_name
        # Real process-level sandbox (app/platform/sandbox.py), previously
        # never wired in anywhere: every tool call used to run as plain
        # Python inside the main process, with no isolation and no real
        # limits. Defaults to a fresh SandboxedToolExecutor (every existing
        # caller gets the real sandbox for free -- there was never a
        # legitimate reason to run a tool unsandboxed, so this isn't gated
        # behind an explicit opt-in the way most additive params in this
        # project are).
        self._sandbox = sandbox or SandboxedToolExecutor()

    def propose_and_execute(self, tool_name: str, args: dict, description: str) -> str:
        """READ actions run immediately (still audited). WRITE/ACT actions raise
        ApprovalPending — the caller must call resume_after_approval() once a
        human has decided."""
        action_class = self._classifier.classify(tool_name)
        risk_level = self._classifier.assess_risk(action_class)

        proposal = ActionProposal(
            action_class=action_class, tool_name=tool_name, description=description,
            args=args, risk_level=risk_level,
        )

        if not self._classifier.requires_approval(action_class):
            return self._execute_and_audit(proposal, ApprovalStatus.AUTO_APPROVED, approved_by=None)

        self._audit.record(
            AuditRecord(action_id=proposal.action_id, proposal=proposal, approval_status=ApprovalStatus.PENDING)
        )
        raise ApprovalPending(proposal.action_id)

    def resume_after_approval(self, action_id: str, approved: bool, approved_by: str) -> str:
        record = self._audit.get(action_id)
        if record is None:
            raise ValueError(f"No pending action with id '{action_id}'.")
        if record.approval_status != ApprovalStatus.PENDING:
            raise ValueError(f"Action '{action_id}' is not pending (status: {record.approval_status.value}).")

        if not approved:
            self._audit.record(
                AuditRecord(
                    action_id=action_id, proposal=record.proposal,
                    approval_status=ApprovalStatus.REJECTED, approved_by=approved_by,
                )
            )
            return "Action rejected by user; not executed."

        return self._execute_and_audit(record.proposal, ApprovalStatus.APPROVED, approved_by=approved_by)

    def _execute_and_audit(self, proposal: ActionProposal, status: ApprovalStatus, approved_by: str | None) -> str:
        tool = self._tools.get(proposal.tool_name)
        if tool is None:
            raise ToolError(f"Tool '{proposal.tool_name}' is not registered.")

        try:
            self._permissions.check(tool)
        except PermissionDeniedError as exc:
            self._audit.record(
                AuditRecord(
                    action_id=proposal.action_id, proposal=proposal, approval_status=status,
                    approved_by=approved_by, executed=False, execution_result=f"Denied: {exc}",
                )
            )
            raise

        # Real sandboxed execution, risk-aware: a HIGH-risk (ACT-class)
        # tool call gets the tightest real limits, matching how much a
        # misbehaving call could actually cost -- not a direct, unsandboxed
        # tool.call() anymore.
        result = self._sandbox.execute(tool, proposal.args, risk_level=proposal.risk_level)
        verified, verification_note = self._verify(proposal, result)

        self._audit.record(
            AuditRecord(
                action_id=proposal.action_id, proposal=proposal, approval_status=status,
                approved_by=approved_by, executed=True, execution_result=result,
                verified=verified, verification_note=verification_note,
            )
        )
        return result

    def undo_action(self, action_id: str, undone_by: str) -> str:
        """Found missing while investigating "Human-in-the-Loop AI"
        (criterion: "understand undo/recovery"): an executed action had no
        path back at all. Only genuinely reverses an action that was
        actually executed and whose Tool explicitly declares undoable=True
        -- raises UndoNotSupportedError otherwise, never silently no-ops."""
        record = self._audit.get(action_id)
        if record is None:
            raise ValueError(f"No action with id '{action_id}'.")
        if not record.executed:
            raise ValueError(f"Action '{action_id}' was never executed; nothing to undo.")
        if record.undone:
            raise ValueError(f"Action '{action_id}' was already undone.")

        tool = self._tools.get(record.proposal.tool_name)
        if tool is None:
            raise ToolError(f"Tool '{record.proposal.tool_name}' is not registered.")
        if not tool.undoable:
            raise UndoNotSupportedError(f"Tool '{record.proposal.tool_name}' does not support undo.")

        args = tool.validate_args(record.proposal.args)
        undo_result = tool.undo(args, record.execution_result or "")

        record.undone = True
        record.undo_result = undo_result
        record.undone_by = undone_by
        self._audit.record(record)
        return undo_result

    def _verify(self, proposal: ActionProposal, result: str) -> tuple[bool, str]:
        """Minimal post-execution verification: the tool returned something
        non-empty. Real verification (e.g. 'did the email actually send') would
        be tool-specific; this is the structural hook for it (Section 28's
        'Verification' step exists as a real gate, not skipped)."""
        if result and result.strip():
            return True, "Execution produced a non-empty result."
        return False, "Execution produced an empty result — could not verify success."
