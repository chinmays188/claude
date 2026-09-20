# Production Architecture (Phase 5, Milestone 44)

## Purpose

This document defines the target deployment architecture for productionizing
the Personal AI OS — what changes when moving from "runs via `python -m
app.main` on a laptop" to "runs as a real, multi-user service." It is a
design document; the milestones that follow (45-60) implement the pieces
that are verifiable inside this sandbox and honestly flag the ones that
aren't (real load, real infra, real incidents).

## Current state (Phases 1-4)

```text
CLI / FastAPI dev server (uvicorn, single process)
        │
        ▼
   app/* (agents, domains, proactive, etc.)
        │
        ▼
   SQLite file on local disk (data/personal_ai.db)
```

Single process, single user, no auth, no queue, no container, local file
storage. This is intentional for Phases 1-4 — the goal there was learning AI
engineering concepts, not operating infrastructure.

## Target production architecture

```text
                              LOAD BALANCER / INGRESS
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              API WORKER 1        API WORKER 2        API WORKER N
              (FastAPI, stateless)
                    │                   │                   │
                    └───────────────────┼───────────────────┘
                                        ▼
                          AUTH LAYER (Milestone 48)
                                        │
                                        ▼
                    APP LOGIC (unchanged from Phases 1-4)
                                        │
                ┌───────────────────────┼───────────────────────┐
                ▼                       ▼                       ▼
          JOB QUEUE                PERSISTENT DB           SECRETS STORE
      (Milestone 46-47)          (replaces SQLite            (Milestone 49)
                │                  file, Milestone 50)
                ▼
          WORKER POOL
      (long-running tasks,
       autonomous research,
       scheduled/event-driven
       agents — Phase 4)
                │
                ▼
        OBSERVABILITY EXPORT
         (Milestone 51: traces/metrics/logs
          shipped to an external collector)
```

## What changes, and why

| Layer | Phase 1-4 | Production target | Milestone |
|---|---|---|---|
| Process model | Single process | Multiple stateless API workers behind a load balancer | 44 (this doc) |
| Packaging | Local Python venv | Docker image, versioned | 45 |
| Long-running work | Synchronous in-process call (`AutonomousResearchRunner.run_to_completion`) | Dispatched to a queue, executed by a worker pool | 46-47 |
| Identity | None — single implicit user | Token-based auth, RBAC | 48 |
| Secrets | `.env` file, gitignored | A secrets store with rotation/access-control rules | 49 |
| Data isolation | `tenant_id`/`owner_id` columns, enforced in application code | Same enforcement mechanism, formalized and tested as a first-class concern | 50 |
| Observability | In-process `TraceRecorder`, nothing exported | Traces/metrics exported in an OpenTelemetry-compatible shape | 51 |
| Failure handling | Guardrails (budgets, retries within `RepairableGenerator`) | Same guardrails PLUS network-level resilience (timeouts, backoff, circuit breakers) for calls to Gemini/GitHub/etc. | 52 |
| Release safety | Manual "did the tests pass" check | An automated evaluation gate blocking a bad prompt/model change from shipping | 53 |
| Model/prompt changes | Direct edit to a Python constant | Versioned, with a rollback path | 54 |
| Cost control | `CostTracker` reports after the fact | Budgets that can actually alert/block before overspend | 55 |

## What this document does NOT claim

Per Phase 5's scope decision, this architecture is a target design, not a
deployed reality. Specifically NOT true of this codebase after Phase 5:

- There is no real load balancer, no real multi-worker deployment running
  anywhere.
- There is no real external queue broker (Redis/RabbitMQ/SQS) wired up — the
  queue abstraction (Milestone 46) is a real, tested in-process implementation
  with an interface a real broker could later satisfy.
- There is no real external secrets manager (Vault/AWS Secrets Manager)
  integration — the secrets loader (Milestone 49) enforces real rules
  (no secrets in code, required rotation metadata) against local `.env`-style
  sources.
- There is no real Prometheus/Grafana stack scraping this service.
- Milestones 56-60 (load testing, disaster recovery, security testing,
  control plane, production readiness review) describe what a real
  production rollout requires; each is addressed with the deepest artifact
  that's honestly verifiable without real infrastructure or real traffic
  (a runnable load-test script, a documented DR runbook, a security-testing
  checklist run against this codebase, etc.) — see each milestone's own spec
  file for exactly what was built vs. documented as a gap.

## Design principle carried from Phases 1-4

Every production concern added in Phase 5 wraps or extends existing,
already-tested Phase 1-4 components rather than replacing them. The
guardrails, evaluation framework, and safety model built in Phases 1-3 are
the actual AI-quality foundation; Phase 5 makes that foundation deployable,
it does not re-architect it.
