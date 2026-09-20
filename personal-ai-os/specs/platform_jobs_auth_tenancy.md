# Async Jobs, Workflow Runtime, Auth, Secrets, Multi-Tenancy (Milestones 46-50)

## Milestone 46 — Async Jobs & Queues

### Example 1 — Enqueue/dequeue is real and durable

Input: a job enqueued to the "emails" queue.

Expected:
- `JobQueue.dequeue()` claims the oldest `QUEUED` job (FIFO), marking it
  `IN_PROGRESS` and incrementing `attempts`
- SQLite-backed — a job survives across `JobQueue` instances wrapping the
  same connection, same durability pattern as every other store in this project

### Example 2 — Retry vs. dead-letter is bounded, never infinite

Input: a job failed repeatedly.

Expected:
- Each failure re-queues the job until `attempts >= max_attempts`, then moves
  it to `DEAD_LETTER` — never retried forever, and never silently dropped
- `dead_letter_jobs()` makes stuck jobs discoverable for manual intervention

### Honest scope note

No real external broker (Redis/RabbitMQ/SQS) is integrated — this is a real,
tested, SQLite-backed in-process queue. Its interface
(`enqueue`/`dequeue`/`complete`/`fail`) is exactly what a real
broker-backed implementation would need to satisfy, so swapping the backend
later is a substitution, not a redesign.

## Milestone 47 — Persistent Workflow Runtime

### Example — A workflow is durable across the queue AND the task state machine

Input: `WorkflowRuntime.submit()` for a registered workflow type.

Expected:
- Creates a `LongRunningTask` (Phase 2, Milestone 26) AND enqueues a job
  (Milestone 46) referencing that task
- `process_one()` (a worker's loop body) drives the task through
  `PLANNING -> RUNNING -> EVALUATING -> COMPLETED`, or `-> FAILED` on a
  handler exception — and reports success/failure back to the queue, so a
  failed workflow gets the queue's retry/dead-letter treatment too
- An unregistered workflow type is rejected at `submit()` time, before
  anything is created

## Milestone 48 — Authentication & Authorization

### Example 1 — Tokens are genuinely signed and verified

Input: a token issued by `TokenIssuer`.

Expected:
- `verify()` on the correct issuer/secret succeeds and returns the original
  payload
- A tampered payload, or verification with the wrong secret key, is rejected
  via `hmac.compare_digest` (constant-time comparison — not `==`, to avoid a
  timing side-channel)
- An expired token raises `TokenExpiredError` specifically, distinct from a
  malformed/tampered one (`InvalidTokenError`), so a caller can distinguish
  "log in again" from "something is wrong with this token"

### Example 2 — Roles map to real, distinct permission sets

Input: `Role.VIEWER` / `Role.OPERATOR` / `Role.ADMIN`.

Expected:
- `permissions_for_role()` returns strictly increasing permission sets —
  VIEWER has no write permissions, OPERATOR has writes but not
  `admin:tenant`, ADMIN has everything
- These permission strings are the same ones Phase 2's `PermissionChecker`
  (Milestone 16) already checks against tools — auth issues an identity;
  Phase 2's existing enforcement mechanism is unchanged and reused, not
  replaced

## Milestone 49 — Secrets & Data Security

### Example 1 — Secrets require registration with rotation metadata

Input: `SecretsProvider.get("SOME_KEY")` for a key never registered.

Expected:
- Raises `SecretNotFoundError` — a secret cannot be silently read from the
  environment without first being declared with rotation metadata

### Example 2 — Overdue rotation is a hard stop, not a warning

Input: a registered secret whose `last_rotated_at` is older than its
`rotation_interval_days`.

Expected:
- `get()` raises `SecretRotationOverdueError` rather than returning the
  stale-but-still-valid secret — forces the rotation conversation to happen
  before the secret is used again, rather than silently allowing an
  indefinitely-unrotated credential

### Example 3 — A real (minimal) secret scanner

Input: text containing a Google-API-key-shaped or GitHub-token-shaped string.

Expected:
- `scan_for_hardcoded_secrets()` flags it — this exact failure mode (a real
  Anthropic key + Gmail app password accidentally committed in a
  `.env.example`) already happened once in this project's history (see
  `.claude/knowledge/github.md`'s log for `job-agent`'s first push) and was
  only caught by GitHub's own secret scanning after the fact; this gives the
  project its own first line of defense

### Honest scope note

No real external secrets manager (Vault/AWS Secrets Manager) is integrated —
`SecretsProvider` reads from environment variables, same as the project's
existing `.env` convention, but now enforces real rules (registration,
rotation) on top of that source.

## Milestone 50 — Multi-Tenant Architecture

### Example — Cross-tenant access is a hard, structural rejection

Input: a `TenantContext` scoped to tenant `t1`, checked against a resource
belonging to tenant `t2`.

Expected:
- `enforce_same_tenant()` raises `CrossTenantAccessError`
- `TenantContext.from_token_payload()` derives tenant/user/role from a
  *verified* token payload (Milestone 48), never from a raw, spoofable
  request parameter — formalizing a rule that was already true throughout
  Phase 2/3 (every store already takes explicit `tenant_id`/`owner_id`
  parameters) as a single, reusable, testable utility rather than trusting
  each call site to get it right independently

## Design principle across all five milestones

None of Milestones 46-50 replace anything built in Phases 1-4. `JobQueue`
wraps around calling existing agents/handlers; `WorkflowRuntime` reuses Phase
2's exact `LongRunningTask` state machine; `TokenIssuer`/`Role` feed into
Phase 2's existing `PermissionChecker`; `TenantContext` formalizes a pattern
every Phase 2/3 store already implements. Phase 5 makes the existing
foundation deployable — it does not re-architect it (see
`docs/production_architecture.md`'s stated design principle).
