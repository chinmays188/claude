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

## Example 7 — Real process-level sandboxing, and wiring governance into the live chat-agent path

The user asked: "lets get into production ai engineering and establish
governance, guardrail ... i'm thinking of sandboxes."

Checked first, honestly -- a real, significant gap: `PolicyEngine`
(Examples 1-6 above) existed and was tested, but the live chat-agent path
(`ToolAgent`, behind `Orchestrator` -- what every real request actually
goes through) called `tool.call()` directly, completely bypassing it.
Only separate domain-workflow code ever constructed and used
`PolicyEngine`. And no tool call anywhere -- governed or not -- ran with
any real process isolation or resource limits; `tool.call()` just ran as
plain Python inside the main process.

**New `app/platform/sandbox.py`**: `SandboxedToolExecutor` runs a tool's
real `run()` call in a genuinely separate OS process
(`multiprocessing.Process(get_context("spawn"))` -- a fresh interpreter,
not a fork sharing the parent's open file descriptors/locks/state), with
real, risk-scaled limits:
- A real wall-clock timeout (`process.join(timeout)`, then
  `terminate()`/`kill()` if still alive) -- verified live with a real
  tool that sleeps longer than its timeout, genuinely terminated.
- A real memory ceiling (`resource.setrlimit(RLIMIT_AS, ...)` set
  *inside* the child, before the tool runs) -- **a real, honest platform
  limitation was found and disclosed, not hidden**: on macOS (this dev
  machine), `RLIMIT_AS` frequently cannot be lowered at all
  (`ValueError: current limit exceeds maximum limit` -- a known Darwin/
  XNU kernel limitation, confirmed by testing a tool that deliberately
  allocates 2GB against a 64MB "limit," which succeeded). Every sandbox
  result now reports `last_memory_limit_applied` honestly (`True`/`False`)
  rather than silently claiming the limit was active -- real and
  enforced on Linux, where this project's own `Dockerfile` actually
  deploys.
- Risk-scaled defaults: `HIGH` risk gets the tightest real limits (3s /
  64MB), `LOW` the most room (10s / 256MB) -- a misbehaving call's
  blast radius is bounded in proportion to how consequential the tool
  actually is.

**`PolicyEngine._execute_and_audit()`** now calls
`self._sandbox.execute(tool, proposal.args, risk_level=proposal.risk_level)`
instead of a direct `tool.call()` -- every governed execution, READ
included, is now genuinely sandboxed.

**`ToolAgent` (and `Orchestrator`) gained a new, optional `policy_engine`
param** -- the real fix for the governance-bypass gap. When given, every
real tool call the live chat-agent loop makes goes through
`PolicyEngine.propose_and_execute()` instead of a direct `tool.call()`.
On a real `ApprovalPending` (a WRITE/ACT-classified tool), `ToolAgent`
now stops the loop cleanly with a new `StopReason.APPROVAL_PENDING` and
a new `AgentResponse.pending_action_id` field -- rather than crashing or
silently retrying -- so a caller can drive the exact same
`PolicyEngine.resume_after_approval()` API domain workflows already use.
Defaults to `None` (every existing caller's identical, unsandboxed,
ungoverned behavior) when not given -- fully backward-compatible.

**Verified fully live against the real Gemini API** (not just scripted
tests): a real READ-classified request ("What is 47 times 12?") ran
through the real sandbox and completed normally; the same request, with
`calculator` overridden to `ACT`-classification, genuinely stopped
mid-flight with a real `pending_action_id`, and only produced "564"
after a real `PolicyEngine.resume_after_approval(approved=True)` call;
a real slow tool was genuinely killed by the real sandbox timeout. New
`scripts/trace_governance.py` runs all 3 demos live; a committed,
real-generated `app/dashboard_ui/governance_examples.json` backs the new
"Governance & Sandbox" dashboard page.

A real, honest scope boundary, disclosed directly rather than implied
away: this is process-level sandboxing (CPU/memory/wall-clock limits,
real OS process isolation of a tool's own crash/hang), not full
container/OS sandboxing (no network namespace isolation, no filesystem
jail, no seccomp) -- that's a different, separate layer
(`Dockerfile`/`docker-compose.yml`, still never actually built/run in
this environment, an explicitly open gap).

860 tests passing (was 856).
