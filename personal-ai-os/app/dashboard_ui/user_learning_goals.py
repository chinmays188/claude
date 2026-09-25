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
(domain=LEARNING), seeded with the user's explicitly chosen defaults:
priority=0.5, progress=0.0, no deadline -- to be updated by the user later
as their actual learning progresses, not invented here.

This intentionally replaced the 4 previously-seeded fabricated demo goals
(one per domain), per the user's explicit choice: "Remove them — replace
with the 15 learning goals only for now." Real personal domain goals
(Career/PM/Finance/Learning, distinct from this capability-tracking list)
were discussed but not yet specified — a separate, later step.
"""

from app.domains.cross_domain.goal_store import GoalStore
from app.domains.cross_domain.models import Goal, GoalStatus
from app.domains.router import Domain

USER_ID = "demo_user"  # matches scripts/seed_demo_data.py's USER_ID

# (goal_id, title, success_criteria) -- success_criteria drawn directly from
# the user's own bullet points under each capability, kept verbatim rather
# than paraphrased.
LEARNING_CAPABILITIES: list[tuple[str, str, list[str]]] = [
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
    ),
    (
        "learn_tool_calling_mcp",
        "Tool Calling & MCP",
        [
            "Understand function calling, tool schemas, tool descriptions, argument validation",
            "Understand MCP, tool permissions, tool retries, idempotency",
            "Understand tool failure handling and tool result validation",
        ],
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
    ),
    (
        "learn_ai_memory",
        "AI Memory",
        [
            "Understand that conversation history is not the same as memory",
            "Understand short-term, long-term, profile, preference, goal, decision, and experience memory",
            "Understand memory retrieval, importance, confidence, duplicate detection, decay/update",
        ],
    ),
    (
        "learn_context_engineering",
        "Context Engineering",
        [
            "Understand context selection, ranking, compression, token budgets",
            "Understand retrieval/memory ordering, tool-result placement, lost-in-the-middle",
            "Internalize: the question is the minimum useful context, not the maximum context window",
        ],
    ),
    (
        "learn_model_routing_strategy",
        "Model Routing & Model Strategy",
        [
            "Understand model routing, model fallback, model capability classification",
            "Understand cost vs quality vs latency trade-offs and provider abstraction",
            "Understand degraded experiences and when free/open-source models are the right choice",
        ],
    ),
    (
        "learn_multimodal_ai",
        "Multimodal AI",
        [
            "Understand text, voice, image, screenshot, PDF, table, and audio pipelines",
            "Understand voice pipelines (STT -> LLM -> TTS)",
            "Understand image/PDF pipelines (extraction -> understanding -> retrieval -> reasoning)",
        ],
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
    ),
    (
        "learn_ai_cost_latency",
        "AI Cost & Latency Engineering",
        [
            "Understand token economics, input vs output token cost, caching (including semantic/prompt caching)",
            "Understand TTFT, streaming, retrieval latency, tool latency, parallel tool calls",
            "Be able to reason in terms of cost per successful customer workflow, not just $/million tokens",
        ],
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
    ),
    (
        "learn_ai_product_strategy",
        "AI Product Strategy",
        [
            "Be able to answer: should this be AI? should this be an agent? should we use RAG? should we fine-tune? should this be multi-agent? should AI take the action?",
            "Internalize the decision framework: deterministic logic -> traditional ML -> LLM -> RAG -> tool calling -> agent -> multi-agent -> human approval -> autonomous execution",
            "Be able to explain why each architectural component in this project exists, what failure mode it solves, how it's measured, what it costs, and what trade-off was made",
        ],
    ),
]


def seed_learning_capability_goals(store: GoalStore) -> list[Goal]:
    """Idempotent: fixed goal_ids, INSERT OR REPLACE via GoalStore.create()
    (same pattern as every other store in this project)."""
    goals = []
    for goal_id, title, success_criteria in LEARNING_CAPABILITIES:
        goal = Goal(
            goal_id=goal_id, owner_id=USER_ID, title=title, domain=Domain.LEARNING,
            priority=0.5, status=GoalStatus.NOT_STARTED, progress=0.0,
            success_criteria=success_criteria,
        )
        store.create(goal)
        goals.append(goal)
    return goals
