"""The user's REAL personal learning goals for using this project as an AI
PM learning vehicle -- NOT fabricated demo data like
scripts/seed_demo_data.py's rest of the seed content (fake names, fake
achievements, fake portfolios). Kept in its own clearly-labeled module for
the same reason app/dashboard_ui/example_traces.py is kept separate from
demo_workflow_outputs.py: real content should never be silently mixed in
with a file whose docstring says everything in it is fabricated.

Source: the user gave a detailed 15-capability AI PM learning map (LLM
Fundamentals through AI Product Strategy) describing what this project is
meant to teach an AI PM end to end. Each capability becomes one real Goal
(domain=LEARNING).

PROGRESS VALUES: originally seeded at 0.0 (the user's own explicit choice).
The user then asked Chief of Staff to track these, and to have progress
reflect "both" (a) real project evidence and (b) the user's own
understanding -- but (b) genuinely can't be observed by reading code, so
each `progress` value below is an honest CODE-COVERAGE PROXY only: how much
of that capability this project has actually built, tested, and (where
possible) verified live this session. It is explicitly NOT a claim about
the user's personal comprehension, and is stated as such wherever this
progress is shown. Each entry's `evidence` field is the concrete basis for
its score, so the number is never presented as a bare assertion.
"""

from app.domains.cross_domain.goal_store import GoalStore
from app.domains.cross_domain.models import Goal, GoalStatus
from app.domains.router import Domain

USER_ID = "demo_user"  # matches scripts/seed_demo_data.py's USER_ID

# (goal_id, title, success_criteria, progress, evidence) -- success_criteria
# drawn directly from the user's own bullet points under each capability,
# kept verbatim rather than paraphrased. progress/evidence are the
# code-coverage-proxy assessment described in the module docstring above.
LEARNING_CAPABILITIES: list[tuple[str, str, list[str], float, str]] = [
    (
        "learn_llm_fundamentals",
        "LLM Fundamentals",
        [
            "Understand LLMs and tokens, context windows",
            "Understand prompting/prompt engineering and structured outputs",
            "Understand function/tool calling, temperature and model parameters",
            "Understand streaming and latency (TTFT vs generation latency)",
            "Understand model limitations, hallucinations, and model selection/routing",
        ],
        0.85,
        "Real structured-output generation+repair (app/structured/repair.py), real tool "
        "calling (ToolAgent), multiple real GeminiProvider calls verified live throughout "
        "this session (routing, agents, trace tooling).",
    ),
    (
        "learn_rag_retrieval",
        "RAG & Retrieval",
        [
            "Understand embeddings, vector databases, chunking",
            "Understand semantic search, keyword search, hybrid retrieval, reranking",
            "Understand retrieval pipelines, context construction, citation/attribution",
            "Understand retrieval freshness and RAG failure modes",
            "Understand RAG evaluation: Recall@K, Precision@K, groundedness, attribution, citation quality",
        ],
        0.75,
        "Real embeddings (SentenceTransformerEmbedding) + real FAISS (VectorStore) + "
        "SecureRetriever permission-filtered grounding, verified live multiple times "
        "(trace_resume.py, analyze_jd tool). retrieval_eval.py's recall/precision exist "
        "but need labeled ground truth not yet built for live queries.",
    ),
    (
        "learn_tool_calling_mcp",
        "Tool Calling & MCP",
        [
            "Understand function calling, tool schemas, tool descriptions, argument validation",
            "Understand MCP, tool permissions, tool retries, idempotency",
            "Understand tool failure handling and tool result validation",
        ],
        0.55,
        "Full Tool/ToolRegistry/ToolAgent decision loop real, tested, and verified live "
        "with 8 real tools. No actual MCP (Model Context Protocol) integration exists in "
        "this codebase -- the tool-calling half is solid, the MCP half is not started.",
    ),
    (
        "learn_agents_multiagent",
        "Agents & Multi-Agent Orchestration",
        [
            "Understand the difference between an LLM application and an agent (plan/tool/observe/reason/verify loop)",
            "Understand agent loops, planning, delegation, specialization, handoffs",
            "Understand state management, agent depth, loop/tool budgets, stop conditions, recovery paths",
            "Understand multi-agent orchestration and know when an agent is necessary vs. a deterministic workflow",
        ],
        0.4,
        "Single-agent dispatch (Orchestrator picks exactly one of Research/Analyst/Planner "
        "per request) real and tested, with real budgets/stop-conditions. Genuine "
        "multi-agent coordination (multiple agents collaborating on one input) does not "
        "exist yet -- actively being built next.",
    ),
    (
        "learn_ai_memory",
        "AI Memory",
        [
            "Understand that conversation history is not the same as memory",
            "Understand short-term, long-term, profile, preference, goal, decision, and experience memory",
            "Understand memory retrieval, importance, confidence, duplicate detection, decay/update",
        ],
        0.5,
        "PersistentMemoryStore (SQLite) real, with importance/confidence fields and a "
        "write policy. Retrieval is naive keyword-overlap only (naive_relevance.py, "
        "explicitly documented as NOT semantic search) -- the storage half is solid, the "
        "retrieval-quality half is a known, disclosed gap.",
    ),
    (
        "learn_context_engineering",
        "Context Engineering",
        [
            "Understand context selection, ranking, compression, token budgets",
            "Understand retrieval/memory ordering, tool-result placement, lost-in-the-middle",
            "Internalize: the question is the minimum useful context, not the maximum context window",
        ],
        0.35,
        "Token/turn/tool-call budgets real (app/guardrails/budgets.py) and a "
        "PersonalContextEngine/ContextBuilder exist, but no real context ranking, "
        "compression, or lost-in-the-middle handling has been built or tested.",
    ),
    (
        "learn_model_routing_strategy",
        "Model Routing & Model Strategy",
        [
            "Understand model routing, model fallback, model capability classification",
            "Understand cost vs quality vs latency trade-offs and provider abstraction",
            "Understand degraded experiences and when free/open-source models are the right choice",
        ],
        0.45,
        "FallbackProvider (tries providers in order, records which served the response) "
        "is real and tested. No real cost/quality-based dynamic routing logic (e.g. "
        "routing simple classification to a cheaper model) has been built.",
    ),
    (
        "learn_multimodal_ai",
        "Multimodal AI",
        [
            "Understand text, voice, image, screenshot, PDF, table, and audio pipelines",
            "Understand voice pipelines (STT -> LLM -> TTS)",
            "Understand image/PDF pipelines (extraction -> understanding -> retrieval -> reasoning)",
        ],
        0.2,
        "app/multimodal/gemini_multimodal.py and a voice session/API exist (real STT "
        "browser API -> /voice/turn -> TTS in dashboard_app's voice page), but neither has "
        "been deeply exercised or verified live this session -- the thinnest area so far.",
    ),
    (
        "learn_ai_evaluation",
        "AI Evaluation",
        [
            "Understand golden datasets, regression tests, adversarial tests",
            "Understand LLM-as-a-judge and human evaluation",
            "Understand task completion, groundedness, hallucination, retrieval recall, tool correctness, citation quality",
            "Be able to ask 'how do we know the AI actually got better' instead of 'the demo looks better'",
        ],
        0.8,
        "The single most-built area: real golden sets, regression comparison, adversarial "
        "failure matrix, LLM-as-judge, human eval harness, retrieval eval -- 24 files under "
        "app/evaluation/, more test coverage here than any other capability.",
    ),
    (
        "learn_ai_safety_guardrails",
        "AI Safety & Guardrails",
        [
            "Understand prompt injection defense, permission boundaries, data leakage prevention",
            "Understand tool permissions, action policies, sensitive data handling, tenant isolation",
            "Understand approval workflows, risk classification, output validation",
            "Internalize: AI products need a policy layer around the model, not just a system-prompt instruction",
        ],
        0.65,
        "Real PolicyEngine, ActionProposal/RiskLevel classification, AuditLog, tenant "
        "isolation (TenantContext) all built and tested. A real (if limited-scope) security "
        "scanner exists (app/platform/security_testing.py) but hasn't been adversarially "
        "extended beyond its own documented scope.",
    ),
    (
        "learn_human_in_the_loop",
        "Human-in-the-Loop AI",
        [
            "Understand the propose -> approve -> execute -> verify loop",
            "Understand approval workflows, action proposals, risk levels, permission systems",
            "Understand undo/recovery, audit trails, verification",
            "Internalize: the best agentic UX is often bounded autonomy, not full autonomy",
        ],
        0.6,
        "Real propose -> approve -> execute -> verify flow via ActionProposal/"
        "ApprovalStatus/PolicyEngine/AuditRecord, exercised in tests and the seed data's "
        "own audit-log entries (one auto-approved READ, one PENDING ACT).",
    ),
    (
        "learn_ai_observability",
        "AI Observability",
        [
            "Be able to track latency, tokens, cost, model, prompt, retrieval, tool calls, errors, agent steps, eval score per request",
            "Understand traces, spans, LLM observability",
            "Understand error rates, model drift, tool failures, retrieval failures",
            "Internalize: you can't product-manage an AI system you can't see the reasoning behind",
        ],
        0.7,
        "Real TraceRecorder/Span/TraceStore, real per-call token/cost tracking, and (this "
        "session) a genuinely readable input-to-output Journey view built and verified live "
        "in the dashboard's Traces page.",
    ),
    (
        "learn_ai_cost_latency",
        "AI Cost & Latency Engineering",
        [
            "Understand token economics, input vs output token cost, caching (including semantic/prompt caching)",
            "Understand TTFT, streaming, retrieval latency, tool latency, parallel tool calls",
            "Be able to reason in terms of cost per successful customer workflow, not just $/million tokens",
        ],
        0.6,
        "Real per-call token usage tracking (GeminiProvider's track_usage) and real "
        "$/request cost computation (CostTracker), verified live for full trace runs "
        "(router + agent turns). No caching layer (semantic or prompt) has been built.",
    ),
    (
        "learn_production_ai_engineering",
        "Production AI Engineering",
        [
            "Understand APIs, async jobs, queues, workers, persistent workflows, Docker",
            "Understand auth, RBAC, secrets, multi-tenancy, reliability, retries, backoff, circuit breakers",
            "Understand rate limiting, disaster recovery, load testing, CI/CD, rollbacks",
            "Understand AI-specific production concepts: prompt/model/tool versioning, eval-gated deployments, AI SLOs, AI incident management",
        ],
        0.5,
        "Real job queue, HMAC-signed auth/RBAC, secrets rotation, tenancy, reliability "
        "(retry/backoff/circuit-breaker), CI workflow, release/rollback, and a real load "
        "test all exist and are tested -- but Docker itself has never actually been run in "
        "this environment (an honestly disclosed, still-open gap).",
    ),
    (
        "learn_ai_product_strategy",
        "AI Product Strategy",
        [
            "Be able to answer: should this be AI? should this be an agent? should we use RAG? should we fine-tune? should this be multi-agent? should AI take the action?",
            "Internalize the decision framework: deterministic logic -> traditional ML -> LLM -> RAG -> tool calling -> agent -> multi-agent -> human approval -> autonomous execution",
            "Be able to explain why each architectural component in this project exists, what failure mode it solves, how it's measured, what it costs, and what trade-off was made",
        ],
        0.3,
        "The decision framework exists implicitly across this project's own scope "
        "decisions (documented in specs/*.md's 'Scope decision' sections throughout), but "
        "there's no single dedicated artifact that makes this reasoning explicit and "
        "reusable -- the weakest-tracked of the 15, despite being arguably practiced the most.",
    ),
]


def seed_learning_capability_goals(store: GoalStore) -> list[Goal]:
    """Idempotent: fixed goal_ids, INSERT OR REPLACE via GoalStore.create()
    (same pattern as every other store in this project)."""
    goals = []
    for goal_id, title, success_criteria, progress, evidence in LEARNING_CAPABILITIES:
        status = GoalStatus.NOT_STARTED if progress == 0.0 else GoalStatus.IN_PROGRESS
        goal = Goal(
            goal_id=goal_id, owner_id=USER_ID, title=title, domain=Domain.LEARNING,
            priority=0.5, status=status, progress=progress,
            success_criteria=success_criteria + [f"[Progress basis] {evidence}"],
        )
        store.create(goal)
        goals.append(goal)
    return goals
