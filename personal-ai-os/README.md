# Personal AI OS

A voice-first personal AI operating system, built as a hands-on AI engineering
learning lab across 5 phases and 60 milestones — from a single-agent CLI tool
to a proactive Chief of Staff with production-platform patterns layered on top.

```text
Phase 1 → AI Engineering Foundation        (Milestones 1-17)
Phase 2 → Personal Intelligence Layer      (Milestones 18-29)
Phase 3 → Personal Domain OS               (Milestones 30-43, spec numbering restarts per-phase)
Phase 4 → Autonomous Chief of Staff        (Milestones 30-43, own numbering)
Phase 5 → Production AI Platform           (Milestones 44-60)
```

**682 tests, all passing, no API key required to run them.** Every LLM-driven
component has been separately verified against the live Gemini API using
synthetic/example data — never real personal, financial, or career data.

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GEMINI_API_KEY (only required key)

pytest                              # 682 tests, offline, no API key needed
python -m app.main "Explain RAG."   # CLI entry point (Phase 1)
uvicorn app.api.voice_api:app --reload   # voice interface (Phase 2), then open http://localhost:8000
```

---

## How this repo is organized

```text
app/            All source code, one subpackage per capability area (see below)
specs/          One spec-by-example file per milestone — input/expected-output
                examples, not prose "the system shall..." requirements
evals/          Golden datasets and adversarial test fixtures, organized by
                domain (career/pm/finance/learning/cross_domain) and by kind
                (golden/regression/adversarial/human)
tests/          pytest suite mirroring specs/ 1:1 — 682 tests, all offline
docs/           Design/architecture documents that don't fit the spec-by-
                example format (production architecture, DR runbook, the
                detailed Phase 1-2 design-notes reference)
experiments/    Standalone experiment write-ups (e.g. model adaptation)
scripts/        Runnable operational tooling (e.g. the load test)
data/           SQLite database + raw/processed document storage (gitignored)
```

**The governing spec documents** for each phase live at the repo root:
`Personal AI Operating System.md` (Phase 1), `phase-2.md`, `phase-3.md`,
`phase-4.md`, `phase-5.md`. Every milestone below traces back to a numbered
section in one of these.

---

## Phase 1 — AI Engineering Foundation

**The question this phase answers:** *how do you build, evaluate, and safely
operate an AI agent system* — not just make one that works once.

| # | Milestone | Key idea |
|---|---|---|
| 1 | Basic Agent | Swappable `LLMProvider` — agents never call Gemini's SDK directly |
| 2 | Multi-Agent Orchestration | Classifier routes to Research/Analyst/Planner; never guesses on ambiguous input |
| 3 | Tool Calling | Pydantic-validated args, a hallucination-proof `ToolRegistry` |
| 4 | Structured Output Reliability | Repair loop on malformed JSON, then a provider fallback chain |
| 5 | Agent Guardrails | Turn/tool/token/time budgets — tested against a real runaway-loop scenario |
| 6 | Voice | *Skipped* — CLI-only project, no browser frontend yet |
| 7 | Retrieval | Chunking, local embeddings, FAISS vector search |
| 8 | Retrieval Evaluation | Recall, precision, grounding, citation quality |
| 9 | Hybrid Retrieval | BM25 + vector fusion, cross-encoder reranking |
| 10 | Context Engineering | Ordered/prioritized context builder, lost-in-the-middle harness |
| 11 | Evaluation System | Golden sets, regression detection, adversarial tests, LLM-as-judge, human eval |
| 12 | Observability | Traces, nested spans, latency |
| 13 | Cost Engineering | Per-component and per-model journey cost attribution |
| 14 | Model Routing | Task-complexity → model-tier routing |
| 15 | Caching | Prompt cache + semantic cache with a staleness guard |
| 16 | Safety | Prompt injection framing, tool permission enforcement, memory isolation |
| 17 | Model Adaptation | ICL vs. RAG vs. fine-tuning vs. distillation decision framework |

**A real bug was found and fixed here:** Gemini sometimes wraps JSON in
markdown fences with unescaped literal newlines inside string values —
`ToolAgent` was silently leaking the raw broken text to the user. Fixed with
a lenient JSON parser plus routing the decision step through the repair loop.
Full writeup: [`docs/phase1_2_design_notes.md`](docs/phase1_2_design_notes.md).

**Full detail:** [`docs/phase1_2_design_notes.md`](docs/phase1_2_design_notes.md) ·
specs: [`specs/basic_agent.md`](specs/basic_agent.md) through [`specs/model_adaptation.md`](specs/model_adaptation.md)

---

## Phase 2 — Personal Intelligence Layer

**The question this phase answers:** *can the system understand my personal
context, knowledge, history, and current situation* — not just perform a
generic AI task.

| # | Milestone | Key idea |
|---|---|---|
| 18 | Voice Interface | FastAPI + browser Web Speech API, session continuity |
| 19 | Personal Knowledge Ingestion | 6 file formats; owner/tenant/sensitivity access control enforced in code, never by the LLM |
| 20 | Long-Term Memory | SQLite-backed, 9 memory types, a real write policy (not every conversation is saved) |
| 21 | Personal RAG | Memory + documents kept distinguishable, never merged before reaching the LLM |
| 22 | Multimodal Understanding | Images/screenshots/PDFs via Gemini; adversarial image-injection checks |
| 23 | Personal Context Engine | Item-level relevance/importance/freshness/confidence scoring |
| 24 | Real-World Integrations | Real read-only GitHub client; stub Calendar/Email with the same interface |
| 25 | Human Approval & Action Layer | READ/WRITE/ACT classes, propose→approve→execute→verify→audit |
| 26 | Long-Running Tasks | SQLite-backed state machine, checkpointing, pause/resume/retry/cancel |
| 27 | Personal Event & Decision Graph | "Why did I make this decision?", answerable from stored data |
| 28 | Personal OS Evaluation | Career/learning/PM/personal-knowledge golden sets |
| 29 | Personal AI Dashboard | Data layer only (no UI) — see scope decisions below |

**Scope decisions made explicitly, not by default:** voice built as a real
interaction surface (not skipped, unlike Phase 1); GitHub is a real
integration, Calendar/Email are interface-compatible stubs (no OAuth setup
required); the dashboard is data-only; memory/tasks/decisions moved to real
SQLite because durability across restarts is the actual point of "long-term."

**Full detail:** [`docs/phase1_2_design_notes.md`](docs/phase1_2_design_notes.md) ·
specs: [`specs/voice_interface.md`](specs/voice_interface.md), [`knowledge_ingestion.md`](specs/knowledge_ingestion.md), [`long_term_memory.md`](specs/long_term_memory.md), [`personal_rag.md`](specs/personal_rag.md), [`multimodal.md`](specs/multimodal.md), [`personal_context_engine.md`](specs/personal_context_engine.md), [`integrations.md`](specs/integrations.md), [`action_layer.md`](specs/action_layer.md), [`long_running_tasks.md`](specs/long_running_tasks.md), [`decision_graph.md`](specs/decision_graph.md), [`personal_evaluation.md`](specs/personal_evaluation.md), [`dashboard.md`](specs/dashboard.md)

---

## Phase 3 — Personal Domain OS

**The question this phase answers:** *can one shared AI infrastructure power
career, product management, finance, and learning workflows* while keeping
domain-specific safety and evaluation — not four unrelated chatbots.

**Domain Router** (`app/domains/router.py`) classifies a request into one or
more of `CAREER` / `PM` / `FINANCE` / `LEARNING`, orchestrating cross-domain
requests (e.g. *"Should I learn Kubernetes for my career?"* → CAREER + LEARNING)
rather than forcing a single label.

| Domain OS | Key workflows | The domain's specific safety rule |
|---|---|---|
| **Career** (`app/domains/career/`) | JD analysis, resume optimization, STAR interview prep | Every suggestion traces to a real, retrieved achievement id — never invents experience |
| **Learning** (`app/domains/learning/`) | Explain/analogy/exercise/adaptive evaluation loop | Content is always tagged factual / analogy / speculation |
| **PM** (`app/domains/pm/`) | Feedback intelligence, stakeholder analysis, PRD + Critic Agent, sprint planning | A mandatory Critic Agent challenges every PRD — never rubber-stamps |
| **Finance** (`app/domains/finance/`) | Portfolio analysis, scenario analysis, loan/goal projections | **Never uses an LLM for arithmetic** — every number is computed deterministically and tagged FACT/CALCULATION/ASSUMPTION/OPINION; trade execution is structurally impossible |

**Cross-domain layer** (`app/domains/cross_domain/`): a `GoalAgent` tracking
goals/dependencies/conflicts across domains, a Weekly Review and Daily Brief
grounded only in real source data, and an advisor combining domain
perspectives into one recommendation.

All test fixtures across every domain are fabricated/synthetic — no real
resume, portfolio, or personal data enters this repo, per an explicit scope
decision made before any domain code was written.

**Specs:** [`domain_router.md`](specs/domain_router.md) · [`career_os.md`](specs/career_os.md) · [`learning_os.md`](specs/learning_os.md) · [`pm_os.md`](specs/pm_os.md) · [`finance_os.md`](specs/finance_os.md) · [`cross_domain.md`](specs/cross_domain.md) · [`phase3_remaining_pieces.md`](specs/phase3_remaining_pieces.md) (guardrail registry, domain golden sets, cost/trace/dashboard extensions)

---

## Phase 4 — Autonomous Chief of Staff

**The question this phase answers:** *can the AI proactively notice what
needs attention and propose a plan* — while never executing a consequential
action without approval.

```text
AI → OBSERVE → UNDERSTAND → PRIORITIZE → PROPOSE → APPROVE → ACT → VERIFY → LEARN
```

- **Event & Trigger Engine + Attention Engine** (`app/proactive/events.py`,
  `triggers.py`, `attention.py`): a pub/sub bus, deterministic (non-LLM)
  trigger rules, and attention scoring with real notification deduplication.
- **Commitment & Follow-up Manager, Goal & Progress Monitor**
  (`commitments.py`, `goal_monitor.py`): LLM-based commitment *detection*
  (a genuine judgment call) but deterministic overdue-checking; bridges
  Phase 3's `GoalAgent` into this event system.
- **Autonomous Research, Action Plans, Outcome Tracking**
  (`autonomous_research.py`, `action_plans.py`, `outcome_tracking.py`):
  long-running research tasks driven through Phase 2's exact task state
  machine; multi-step plans that drop any hallucinated tool outright and
  route every step through Phase 2's unchanged `PolicyEngine` for approval;
  outcome tracking distinct from per-call verification (`success_rate()`
  is `None`, never `0.0`, until something actually resolves).
- **Personal Decision Engine, Chief of Staff Orchestrator**
  (`decision_engine.py`, `chief_of_staff.py`): the one component that decides
  how much response a signal deserves (never acts itself), sequenced by an
  orchestrator with no trigger/scoring/plan logic of its own.
- **Proactive AI Evaluation** (`app/evaluation/proactive_eval.py`): false
  positive and false negative rates reported as two separate numbers —
  never blended, since annoying the user and missing something important
  are very different failure costs.

**Scope decision:** no real always-on background poller exists — every
event/trigger/attention/scheduling *logic* path is real and tested; only
"what calls this on a timer forever" is deferred, since this sandbox has no
long-lived process to host it.

**Specs:** [`event_trigger_attention.md`](specs/event_trigger_attention.md) · [`chief_of_staff.md`](specs/chief_of_staff.md)

---

## Phase 5 — Production AI Platform

**The question this phase answers:** *can this operate as a reliable
production AI platform* — and, honestly, mostly not yet. This phase built
real, tested **patterns** for production concerns and disclosed every gap
that needs real infrastructure to close.

| Area | What's real and tested | What's an honest, disclosed gap |
|---|---|---|
| Architecture & Docker | `docs/production_architecture.md`; a real `Dockerfile`/`docker-compose.yml`, manually verified | Docker isn't installed in this sandbox — `docker build` was never actually run |
| Jobs & workflows | SQLite-backed job queue with retry/dead-letter; workflow runtime tied to Phase 2's task state machine | No real external broker (Redis/RabbitMQ/SQS) |
| Auth & tenancy | Real HMAC-signed tokens, RBAC feeding Phase 2's `PermissionChecker`, cross-tenant rejection | No real external identity provider |
| Secrets | Registration + rotation-overdue enforcement; a real (minimal) secret scanner | No real external secrets manager |
| Observability | Genuine OpenTelemetry-shaped span export | No real OTel Collector / Prometheus / Grafana instance |
| Reliability | Real timeout, exponential backoff + jitter, circuit breaker | Not yet wired into every external call site (Gemini, GitHub) |
| CI/CD | A real GitHub Actions workflow that will execute on push/PR | Runs the offline suite only — live-API verification stays manual |
| Release management | Real, tested version + rollback | — |
| Cost governance | Pre-flight budget checks | Not yet enforced automatically in a live request path |
| Load testing | A confirmed-working load-test script (50 concurrent requests, 0 errors, p50/p95/p99 reported) | Measures app overhead only — no real infra or live-API load tested |
| Disaster recovery | A full backup→loss→restore→verify drill, tested end to end | No off-site backup storage; no real infra-failure drill |
| Security testing | A real scanner, run against this codebase (it found and disclosed a false positive on its own source) | Not a maintained tool (Bandit/Semgrep); no third-party audit |
| Control plane | — | Not built — no fleet of deployed instances exists to have a control plane over |

**`docs/production_readiness_review.md`** is the honest, filled-out
checklist against this codebase's actual state — the closing artifact of the
entire project, and the actual answer to Phase 5's key question.

**Specs:** [`production_architecture_and_docker.md`](specs/production_architecture_and_docker.md) · [`platform_jobs_auth_tenancy.md`](specs/platform_jobs_auth_tenancy.md) · [`production_platform.md`](specs/production_platform.md)

---

## Design principles that hold across all 5 phases

- **Spec-by-example, not prose requirements.** Every milestone's behavior is
  defined as input → expected output, plus explicit edge and failure cases
  (`specs/*.md`) — never "the system shall handle errors gracefully."
- **Nothing gets re-architected across phases — it gets extended.** Phase 2
  reuses Phase 1's `LLMProvider`/`RepairableGenerator`/`Tool` machinery.
  Phase 3's domain agents reuse Phase 2's memory, RAG, and action layer.
  Phase 4's Chief of Staff reuses Phase 2's task state machine and
  `PolicyEngine` unchanged. Phase 5 wraps existing components (cost
  tracking, the trace schema, regression comparison) rather than replacing them.
- **The LLM never enforces safety or arithmetic.** Access control
  (`SecureRetriever`), financial math (`app/domains/finance/calculations.py`),
  and trade-execution refusal are all structural, code-level guarantees —
  never a prompt instruction hoping the model complies.
- **Guessing is worse than asking.** The `Orchestrator`, `DomainRouter`, and
  interview-story/resume-optimization workflows all raise or ask for
  clarification rather than fabricating an answer when they're not confident
  or don't have real grounding data.
- **Gaps are disclosed, not hidden.** From Phase 1's failure matrix through
  Phase 5's production readiness review, every "not implemented" or
  "not verified against real infrastructure" is stated explicitly.
- **No real personal, financial, or career data in this repo.** Every domain
  workflow (Career, Finance especially) is tested exclusively against
  fabricated, synthetic fixtures.

---

## Testing

```bash
pytest                    # full suite: 682 tests, offline, no API key needed
pytest tests/test_X.py    # a single module's tests
```

Tests use fake/scripted `LLMProvider`s and fake embedding models throughout —
no network calls, no cost, no flakiness from live API latency. Every
LLM-driven component has *also* been manually verified against the live
Gemini API at least once during development (see each phase's design notes
or spec file for the specific verification run and its output).
