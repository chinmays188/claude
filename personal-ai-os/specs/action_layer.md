# Human Approval & Action Layer

## Example 1 — READ actions execute immediately, no approval

Input:
`propose_and_execute("calculator", {...}, "compute")`.

Expected:
- Executes right away, no `ApprovalPending` raised — matches Section 27's
  exact example (`Read GitHub -> READ, no approval`)
- Still fully audited (`ApprovalStatus.AUTO_APPROVED`) — Section 28: "Every
  action should generate an audit record," including ones that didn't need
  human sign-off

## Example 2 — ACT actions require approval before executing

Input:
`propose_and_execute("send_email", {...}, "notify")`.

Expected:
- Raises `ApprovalPending` instead of executing — matches Section 27's
  `Send email -> ACT, Approval required`
- An audit record is written with `PENDING` status immediately, before any
  human has decided anything, so a proposal is never invisible while awaiting
  approval

## Example 3 — Approval resumes execution; rejection blocks it permanently

Input:
`resume_after_approval(action_id, approved=True/False, approved_by="alice")`.

Expected:
- `approved=True` → tool actually executes, result returned, audit updated
- `approved=False` → tool never executes, audit reflects `REJECTED` — there is
  no code path where a rejected action still runs

## Example 4 — Permission check happens even after approval

Input:
An `ACT` action approved by a human, but the caller's granted permissions don't
include what the tool requires.

Expected:
- `PermissionDeniedError` raised at execution time — human approval is
  necessary but not sufficient; the underlying permission model (Milestone 16)
  still applies. A user cannot approve their way past a permission they don't
  have.

## Example 5 — Unknown or already-resolved action ids are rejected

Input:
`resume_after_approval()` called with an id that was never proposed, or one
that was already approved/rejected.

Expected:
- `ValueError` raised — prevents double-execution or acting on stale approval
  state

## Example 6 — Verification is a real step, not skipped

Input:
A successfully executed action.

Expected:
- `AuditRecord.verified`/`verification_note` are populated — matches Section
  28's architecture diagram (`Tool Execution -> Verification -> Audit Log`) as
  a distinct step, even though this milestone's verification check is
  intentionally minimal (non-empty result)

## Default classification for unknown tools

An unrecognized tool name defaults to `WRITE` (requires approval), never
`READ` — a newly added tool that hasn't been explicitly classified yet should
never silently skip the approval gate.
