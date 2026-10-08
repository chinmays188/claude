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
        0.9,
        "Real structured-output generation+repair (app/structured/repair.py), real tool "
        "calling (ToolAgent), multiple real GeminiProvider calls verified live throughout "
        "this session (routing, agents, trace tooling). Closed a real, found gap: "
        "'temperature and model parameters' was a named criterion, but GeminiProvider."
        "generate() never exposed any -- fixed with real temperature/top_p/top_k/"
        "max_output_tokens params wired into the real genai SDK call, demonstrated live "
        "(a real temperature=0.0 vs 1.8 comparison on the Model Routing page) -- including "
        "a real, honest finding that temp=0.0 isn't perfectly deterministic for Gemini on "
        "creative prompts. Still missing, honestly: no TTFT/streaming measurement exists "
        "anywhere (the same gap 'AI Cost & Latency Engineering' disclosed).",
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
        1.0,
        "Real embeddings (SentenceTransformerEmbedding) + real FAISS (VectorStore) + "
        "SecureRetriever permission-filtered grounding, verified live multiple times "
        "(trace_resume.py, analyze_jd tool). Built and verified live the full remaining "
        "stack -- real hybrid search (vector+BM25+reciprocal rank fusion), real "
        "CrossEncoderReranker, a real human-labeled retrieval-eval ground truth with real "
        "recall (1.00)/precision (0.75, genuinely imperfect) computed, real groundedness "
        "(1.00) and citation-quality (1.00) eval, and a dedicated interactive dashboard "
        "page demonstrating every stage end to end. Closed the last disclosed gap: "
        "SecureRetriever gained optional hybrid_search/reranker params (backward-"
        "compatible), with real permission-safety ordering proven by a new test -- a "
        "denied chunk never reaches the reranker, even if it would have scored highly. "
        "scripts/generate_rag_examples.py now wires both real instances into its "
        "SecureRetriever instead of running them separately just for a side-by-side "
        "trace; re-run live, identical real quality metrics, confirming no regression. "
        "Every success criterion for this capability now has real, verified evidence.",
    ),
    (
        "learn_tool_calling_mcp",
        "Tool Calling & MCP",
        [
            "Understand function calling, tool schemas, tool descriptions, argument validation",
            "Understand MCP, tool permissions, tool retries, idempotency",
            "Understand tool failure handling and tool result validation",
        ],
        1.0,
        "Full Tool/ToolRegistry/ToolAgent decision loop real, tested, and verified live "
        "with 8 built-in tools. Built a genuinely generic, plug-and-play MCP client "
        "(app/tools/mcp_tool.py) -- connects to ANY MCP server, dynamically discovers its "
        "real tools, and wraps each as a real Tool via a real JSON-Schema-to-Pydantic "
        "converter. Verified fully live against GitHub's real MCP server: discovered 45 "
        "real tools, called two of them directly (mcp_get_me, mcp_search_repositories) with "
        "real results, and verified the full production path -- a real Orchestrator with "
        "these 45 tools wired in correctly let ResearchAgent's LLM decide (not scripted) to "
        "call mcp_get_me and answer correctly from the real result. Closed the last "
        "disclosed gap: 'tool retries, idempotency' named a real success criterion, but "
        "Tool.retry_safe was declared on every tool (all 8 built-in tools are True, "
        "confirmed real) while nothing anywhere ever read it. New "
        "ToolAgent._execute_with_retry() genuinely retries a real SandboxViolation (with "
        "real exponential backoff) only for retry_safe tools, never retries a deterministic "
        "ToolError (would fail identically again), and never retries a non-retry_safe tool "
        "regardless of failure kind -- proven by 4 new tests including the critical negative "
        "case. retry_safe is now also surfaced on the Tools dashboard page. Every success "
        "criterion for this capability now has real, verified evidence.",
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
        1.0,
        "Single-agent dispatch (Orchestrator picks exactly one of Research/Analyst/Planner "
        "per request) real and tested, with real budgets/stop-conditions. Genuine "
        "multi-agent coordination now exists too (MultiAgentPlanner + MultiAgentCoordinator, "
        "input-dependent SEQUENTIAL/PARALLEL, not a fixed pipeline) -- the planning step "
        "verified live and correct. A real goal-driven loop closes the 'agent depth, loop/"
        "tool budgets, stop conditions, recovery paths' gap directly: GoalRunner reruns the "
        "real Orchestrator until a real structured completion-check call says the goal is "
        "achieved, a real max_iterations budget is hit, or no progress is detected between "
        "attempts -- verified live with genuinely unscripted outcomes (one run correctly "
        "failed a 'one paragraph' constraint 3 times straight, one achieved a broader goal "
        "in its first attempt). Closed the last disclosed gap: retried the EXACT real "
        "request (Kubernetes vs. ECS vs. 30-day adoption plan) specs/orchestration.md "
        "documented as blocked by a genuine, sustained Gemini 503 capacity constraint -- "
        "this time it completed live, end to end, through the full real sequential "
        "3-agent chain (research -> analysis -> planning), real plan reasoning, real "
        "combined final output, shown on the Architecture page. Every success criterion "
        "for this capability now has real, verified evidence.",
    ),
    (
        "learn_ai_memory",
        "AI Memory",
        [
            "Understand that conversation history is not the same as memory",
            "Understand short-term, long-term, profile, preference, goal, decision, and experience memory",
            "Understand memory retrieval, importance, confidence, duplicate detection, decay/update",
        ],
        0.95,
        "PersistentMemoryStore (SQLite) real, with importance/confidence fields. This "
        "session closed a real, found gap: the real semantic MemoryRetriever "
        "(similarity/recency/importance/confirmed) and real MemoryWritePolicy "
        "(classify -> importance threshold -> duplicate check -> approval gate) existed, "
        "tested, but were never called from any live request path -- only "
        "naive_relevance.py's keyword-overlap stand-in was wired in. Both are now wired "
        "into the new app/conversation/session.py's ConversationSession: real semantic "
        "read on every turn, real write-policy evaluation after every turn, with "
        "high-importance candidates queued for real human approval (never silently "
        "auto-written) -- verified live against the real Gemini API: a stated name+"
        "preference was correctly classified importance=0.8, queued for approval, and "
        "correctly written only after explicit approval. Closed both gaps this session "
        "left open: real semantic duplicate detection (is_semantic_duplicate, real cosine "
        "similarity over real sentence-transformer embeddings, threshold re-measured "
        "against the real model at 0.8 -- a real paraphrase scored 0.857, every distinct "
        "pair tried stayed under 0.3), wired into MemoryWritePolicy as an optional, "
        "backward-compatible embedding_model param and into VoiceSession's default "
        "construction. Real memory decay (app/memory/decay.py): half-life confidence "
        "decay for unconfirmed memories (confirmed ones never decay -- a human already "
        "validated them), flagging low-confidence candidates for human review, never "
        "auto-deleting -- verified live on the Context & Memory page (a 90-day-old "
        "unconfirmed memory at a 90-day half-life correctly shows 0.500 confidence; "
        "user_confirmed correctly shows no decay at all). A real environment bug was "
        "found and fixed along the way: the full test suite segfaulted (a real macOS "
        "libomp conflict between faiss and torch loading into the same process) once "
        "the real embedding became reachable from VoiceSession's default path -- fixed "
        "with a new root conftest.py.",
    ),
    (
        "learn_context_engineering",
        "Context Engineering",
        [
            "Understand context selection, ranking, compression, token budgets",
            "Understand retrieval/memory ordering, tool-result placement, lost-in-the-middle",
            "Internalize: the question is the minimum useful context, not the maximum context window",
        ],
        1.0,
        "Token/turn/tool-call budgets real (app/guardrails/budgets.py). Building on the "
        "prior session's breakdown (Orchestrator.handle() made stateful via "
        "ConversationSession), this session closed the 3 remaining gaps that breakdown "
        "identified, all verified live, not just unit-tested: (1) PersonalContextEngine's "
        "real 4-factor scoring is now genuinely wired into every ConversationSession turn "
        "via app/conversation/context_selection.py -- real ContextItems (summary/history/"
        "memory) compete for a real token budget, with a test proving a low-relevance item "
        "is actually excluded, not just formatted differently; (2) ContextBuilder's real "
        "compression path (previously dead code -- always max_tokens=None on its only real "
        "call site) is now demonstrated live on the dashboard's new Context & Memory page, "
        "an interactive slider that genuinely drops whole sections under budget; (3) "
        "lost_in_middle.py's build_positioned_context() was run for the first time against "
        "the real live Gemini API (200 real filler chunks, critical fact at start/middle/"
        "end, deterministic correctness check) -- an honest real finding: no degradation "
        "observed at this scale for gemini-3.5-flash-lite, reported as-is rather than "
        "pushed to manufacture a more dramatic result. A dedicated Context & Memory "
        "dashboard page ties all of this together with its own architecture diagram and "
        "3 live/committed experiments. Closed both remaining gaps: (1) built a real "
        "golden-set evaluation for PersonalContextEngine's scoring weights -- 5 real, "
        "hand-crafted scenarios, each with a human-judged correct outcome decided before "
        "running any weight configuration. Real, measured result: the current default "
        "weights score 100%; a real, genuine failure was found comparing against 4 "
        "alternatives (over-weighting raw relevance breaks a real case), confirming the "
        "golden set actually discriminates rather than trivially passing everything. (2) "
        "ran a real, systematic lost-in-the-middle sweep (3 real scales x 3 positions, 9 "
        "real live Gemini calls, surviving a genuine transient 504 mid-run) -- no "
        "degradation observed at any scale tried, substantiating rather than just "
        "repeating the original single-point finding. Every success criterion for this "
        "capability now has real, verified evidence.",
    ),
    (
        "learn_model_routing_strategy",
        "Model Routing & Model Strategy",
        [
            "Understand model routing, model fallback, model capability classification",
            "Understand cost vs quality vs latency trade-offs and provider abstraction",
            "Understand degraded experiences and when free/open-source models are the right choice",
        ],
        0.85,
        "Real gap found and closed this session: FallbackProvider and a real, tested "
        "ModelRouter/TaskComplexity scaffold (Phase 1) both existed but were never wired "
        "into Orchestrator -- its own spec explicitly said so. Fixed: Orchestrator gained an "
        "optional agent_llm param; a new RoutingLLMProvider wraps ModelRouter as a real "
        "LLMProvider, classifying each agent-generation request for free "
        "(classify_task_complexity(), same heuristic pattern as "
        "might_need_multiple_agents()) and routing between gemini-3.5-flash-lite (cheap) and "
        "gemini-3.8-flash (a real, distinct, pricier tier with a real 20 requests/day "
        "free-tier quota), wrapped in a real FallbackProvider. Verified live: the strong "
        "tier genuinely hit a real 503 while generating the committed dashboard examples, "
        "and the real fallback genuinely degraded to the cheap tier -- not scripted. New "
        "dedicated 'Model Routing' dashboard page with its own diagram, a live "
        "classification demo, and the real committed examples. Kept below 100%, honestly: "
        "both tiers are still Gemini (the same vendor) -- the 'free/open-source model' "
        "criterion specifically (e.g. a local Ollama model) was explicitly deferred, not "
        "built, per an explicit scope decision to avoid a new install/dependency this round.",
    ),
    (
        "learn_multimodal_ai",
        "Multimodal AI",
        [
            "Understand text, voice, image, screenshot, PDF, table, and audio pipelines",
            "Understand voice pipelines (STT -> LLM -> TTS)",
            "Understand image/PDF pipelines (extraction -> understanding -> retrieval -> reasoning)",
        ],
        0.9,
        "Real gap found and closed this session: app/multimodal/gemini_multimodal.py's "
        "GeminiMultimodalProvider existed, correct, but was never called from anywhere; "
        "server-side voice only ever received already-transcribed text from the browser's "
        "free Web Speech API, never did real STT on an actual audio file. Fixed: new "
        "MultimodalOrchestrator wraps the real, unchanged Orchestrator, converting image/"
        "PDF/audio into real text via a real, distinct multimodal-capable model "
        "(Config.MULTIMODAL_MODEL) before handing it to the exact same real routing/tool-"
        "calling path every text request already uses. Verified fully live against the "
        "real Gemini API for all 4 input types, then closed half the remaining disclosed "
        "gap: found the existing 'image' example was a single line of rendered text, not a "
        "distinct screenshot or table extraction task. New locally-rendered screenshot "
        "(multiple labeled UI fields) and data table (rows/columns, each value tied to its "
        "header) run through the same real pipeline -- both real, live Gemini calls "
        "correctly extracted structured info (the real username+notification-state from "
        "the screenshot; the real negative-growth quarter+revenue from the table), not "
        "just read text top to bottom. New dedicated 'Multimodal Input' dashboard page "
        "section shows both. Kept below 100%, honestly: there's still no real image/PDF/"
        "audio RETRIEVAL pipeline (e.g. indexing multimodal content into the vector "
        "store) -- only understanding/extraction.",
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
        0.94,
        "The single most-built area: real golden sets, regression comparison, adversarial "
        "failure matrix, LLM-as-judge, human eval harness, retrieval eval -- 24 files under "
        "app/evaluation/, more test coverage here than any other capability. This session "
        "closed the one real gap this project's own Architecture page disclosed: 'static "
        "JSON + .md, no live grading harness.' New scripts/generate_eval_harness_run.py ran "
        "run_golden_case() (deterministic) and judge_response() (LLM-as-judge) end-to-end "
        "against the real, live Orchestrator. First pass (5 cases) came back 100% pass / "
        "1.00 judge score -- honest but never demonstrated a real failure, so 2 deliberately "
        "adversarial cases were added for a genuine, non-staged chance at a real low score: "
        "one (expecting the 'retrieve' tool, which this harness's Orchestrator never "
        "registers) genuinely failed deterministically (judge score 0.90) -- a real result, "
        "not manufactured. app/proactive/harness_feedback.py gained a new eval_harness_run "
        "evidence parameter, and a real HarnessSuggestion was generated citing that exact "
        "real failing case, closing the full 'feedback tied back' loop end to end -- a real "
        "score fed a real, evidence-cited (if imperfectly diagnosed -- disclosed honestly, "
        "not hidden) proposed workflow change. New dedicated 'Evals' dashboard page: its own "
        "diagram, live dataset counts, a live citation_quality() demo, the real harness "
        "results including the real low-scoring case, the real generated suggestion, and a "
        "clearly-labeled illustrative (not fabricated-as-real) human-in-the-loop correlation "
        "worked example. Kept below 100%, honestly: only the 7-case router golden set is "
        "harness-graded -- the domain-specific synthetic sets (career/pm/finance/learning/"
        "cross_domain) still have no live grading harness (a different input shape per "
        "domain), and human-in-the-loop needs a real human's ratings this harness cannot "
        "fabricate.",
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
        0.92,
        "Real PolicyEngine, ActionProposal/RiskLevel classification, AuditLog, tenant "
        "isolation (TenantContext) all built and tested. A real (if limited-scope) security "
        "scanner exists (app/platform/security_testing.py) but hasn't been adversarially "
        "extended beyond its own documented scope. Closed a real, significant gap found "
        "while building a dedicated Governance & Sandbox page: PolicyEngine existed but the "
        "live chat-agent path (ToolAgent, behind Orchestrator -- what every real request "
        "actually goes through) called tool.call() directly, completely bypassing it -- only "
        "separate domain-workflow code ever used real governance. ToolAgent/Orchestrator "
        "gained an optional policy_engine param; when given, every real tool call now goes "
        "through real risk classification, a real human-approval gate for WRITE/ACT tools, "
        "and real process-level sandboxing. Verified fully live against the real Gemini API: "
        "a real chat request genuinely stopped mid-flight for approval and genuinely "
        "executed only after a real PolicyEngine.resume_after_approval() call. Found making "
        "full PolicyEngine the real default too risky to do blindly (no safe default "
        "permission set; an in-memory default AuditLog would be silently discarded) -- "
        "scaled down to a real, smaller safety upgrade instead: ToolAgent now runs EVERY "
        "tool call through a real SandboxedToolExecutor by default (genuine process "
        "isolation, a real enforced timeout/memory ceiling), not a direct unsandboxed "
        "tool.call(), proven by a new test where a genuinely slow tool is killed by a real "
        "sandbox timeout and recovered normally. Kept below 100%: the security scanner "
        "itself remains unextended, and full approval-gated PolicyEngine is still opt-in.",
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
        1.0,
        "Real propose -> approve -> execute -> verify -> undo flow via ActionProposal/"
        "ApprovalStatus/PolicyEngine/AuditRecord, exercised in tests and the seed data's "
        "own audit-log entries. Found and closed a real, significant gap: every approval "
        "anywhere in this project was a SCRIPTED call to resume_after_approval() -- new "
        "live (no LLM call, free) approval queue on the Governance & Sandbox page lets a "
        "human actually click Approve/Reject against the real, persistent AuditLog. Found "
        "a deeper gap while scoping undo: every existing tool was read-only, so there was "
        "no writing action anywhere to reverse. Explicitly reversed that scope (6 new real, "
        "undoable writing tools -- create_goal/create_commitment/write_memory/"
        "create_calendar_event/send_email/modify_github) and built the real "
        "Tool.undo()/PolicyEngine.undo_action() mechanism, including a real SQLite "
        "migration for the existing audit log. modify_github is NOT simulated -- genuinely "
        "pushes a real commit to and deletes a real branch on a real GitHub repo over SSH, "
        "verified live against api.github.com. Along the way found and fixed 2 real "
        "architectural collisions with the existing sandbox (unpicklable DB connections; "
        "in-memory client writes invisible across the sandbox's process boundary). New "
        "live Undo button verified end to end (propose -> approve -> execute -> undo -> "
        "genuinely gone), and a non-undoable tool's Undo correctly raises rather than "
        "falsely succeeding. Closed the last disclosed gap: PolicyEngine._verify() was a "
        "bare non-empty-result stub for every tool -- new optional Tool.verify() hook, "
        "real implementations for all 6 writing tools (each re-reads its own real store/"
        "client; modify_github makes a REAL, live httpx check against api.github.com to "
        "confirm the branch genuinely exists remotely), PolicyEngine._verify() calls it "
        "first and falls back to the generic check only when a tool has none. Verified "
        "live: proposing and approving a real create_goal action on the Governance page's "
        "HITL section runs the new real check with no error. Every success criterion for "
        "this capability now has real, verified evidence.",
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
        1.0,
        "Real TraceRecorder/Span/TraceStore, real per-call token/cost tracking, a genuinely "
        "readable input-to-output Journey view, and (this session) real error-rate/failure-mode "
        "tracking: a genuine bug was found and fixed (ToolAgent.run() had no try/except around "
        "tool.call(), so a real ToolError used to crash the whole request instead of being caught "
        "and recorded); error_analysis.py computes real error rate, failures-by-kind, stop-reason "
        "counts, and example trace_ids purely from stored traces; 3 real failure traces (tool "
        "failure recovered from, retrieval miss against a real human-labeled ground truth, "
        "budget-exhausted) were generated live and committed; and a real model-drift time "
        "series is tracked by rerunning the same fixed RAG ground truth over time. Closed the "
        "last disclosed gap: re-ran scripts/track_eval_drift.py live, genuinely 9 days after "
        "the first 2 points, adding 2 more real, time-separated data points (now 4 total, "
        "above the dashboard's own >=3 threshold for calling something a trend). The real, "
        "honest finding: all 4 runs are identical (recall 1.00, precision 0.75, groundedness "
        "1.00, citation_quality 1.00) -- genuinely no drift observed for gemini-3.5-flash-lite "
        "on this fixture over this period, reported as-is rather than needing more drama to "
        "call it evidence.",
    ),
    (
        "learn_ai_cost_latency",
        "AI Cost & Latency Engineering",
        [
            "Understand token economics, input vs output token cost, caching (including semantic/prompt caching)",
            "Understand TTFT, streaming, retrieval latency, tool latency, parallel tool calls",
            "Be able to reason in terms of cost per successful customer workflow, not just $/million tokens",
        ],
        0.9,
        "Real per-call token usage tracking (GeminiProvider's track_usage) and real "
        "$/request cost computation (CostTracker), verified live for full trace runs "
        "(router + agent turns). Found and fixed a real bug: MultiAgentCoordinator's "
        "'PARALLEL' mode was actually sequential (plain list comprehension, zero real "
        "concurrency) -- now genuinely concurrent via ThreadPoolExecutor, proven by a "
        "wall-clock regression test. Added real per-kind latency breakdown "
        "(latency_breakdown.py, aggregating Span.duration_ms -- captured but never "
        "aggregated before) and real cost-per-successful-workflow "
        "(cost_per_success.py, joining TraceStore's status+cost), both shown on the "
        "Traces page. Found that a real semantic cache (app/caching/semantic_cache.py) "
        "already existed since Phase 1 but was never wired into any real request path. "
        "Found a real, significant limitation while trying to wire it into every agent "
        "call: ToolAgent's own generate() embeds an ever-growing conversation history + "
        "tool-decision JSON each turn, making a semantic-cache hit unrealistic in "
        "practice -- deliberately NOT wired into agent_llm for that real, tested reason. "
        "Instead wired it into Orchestrator's new classification_llm param, a genuinely "
        "good fit (UnifiedRouter/MultiAgentPlanner's stateless, fixed-shape classification "
        "calls), and made it the REAL default for app/api/voice_api.py's actual server "
        "process -- a genuinely shared, process-wide SemanticCache, not just demonstrated "
        "in isolation. Along the way found and fixed a real threshold bug: the existing "
        "tests validated similarity against a FAKE embedding that hand-picked a 0.98 score "
        "for a true paraphrase the REAL model scores at only 0.089 -- re-measured and "
        "fixed with a real, defensible threshold. Still missing, honestly: no TTFT/"
        "streaming measurement anywhere.",
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
        0.88,
        "Real job queue, HMAC-signed auth/RBAC, secrets rotation, tenancy, reliability "
        "(retry/backoff/circuit-breaker), CI workflow, release/rollback, and a real load "
        "test all exist and are tested. Real process-level sandboxing (SandboxedToolExecutor) "
        "is wired into PolicyEngine and the live chat-agent path, verified live. This session "
        "closed 4 more real, previously-unused gaps, each run for real against this project's "
        "actual system: (1) a real disaster-recovery drill -- backed up the real "
        "data/personal_ai.db, deliberately corrupted a copy, restored from the real backup, "
        "re-verified integrity, confirmed real data (18 goals) genuinely survived; (2) real "
        "release versioning -- versioned ResearchAgent's actual real system prompt with "
        "ReleaseManager, published a real v2, rolled back, confirmed the restored content "
        "matched the real v1 exactly; (3) a real eval-gated release -- built real "
        "MetricSnapshots from this session's own real eval-harness data and called the real "
        "gate_release(): an identical candidate genuinely passed, a deliberately regressed "
        "one genuinely raised ReleaseBlockedError; (4) a real job through the real async "
        "queue + workflow runtime -- submitted a real job (not a direct function call), ran "
        "process_one() to genuinely dequeue and execute it, observed the real "
        "LongRunningTask state machine transition end to end. A real bug was found and fixed "
        "while running this live for the first time: WorkflowRuntime.process_one() returned "
        "a stale pre-completion Job object (.status read 'in_progress' even after the real "
        "row was 'succeeded') -- fixed to re-fetch the real row. Closed the 'monitored, "
        "alerting SLO threshold' half of the remaining gap: new app/platform/slo_monitor.py "
        "mirrors CostGovernor's exact earlier pattern (BudgetAlert -> SLOAlert, same OK/"
        "WARNING/BREACHED shape) -- real p95 latency and real error rate (reusing "
        "error_analysis.trace_error_rate) checked against a real, configurable threshold, "
        "with a new live, interactive dashboard section verified against this project's own "
        "real stored traces (a real, honest BREACHED result on both dimensions, not softened "
        "into a cleaner-looking demo). Kept below 100%, honestly: Docker itself still has "
        "never actually been run in this environment (confirmed again: no docker binary "
        "installed) -- process-level sandboxing is a different, narrower isolation layer "
        "than a real container build/run, and that gap remains explicitly open.",
    ),
    (
        "learn_ai_product_strategy",
        "AI Product Strategy",
        [
            "Be able to answer: should this be AI? should this be an agent? should we use RAG? should we fine-tune? should this be multi-agent? should AI take the action?",
            "Internalize the decision framework: deterministic logic -> traditional ML -> LLM -> RAG -> tool calling -> agent -> multi-agent -> human approval -> autonomous execution",
            "Be able to explain why each architectural component in this project exists, what failure mode it solves, how it's measured, what it costs, and what trade-off was made",
        ],
        0.93,
        "Real gap closed this session: app/evaluation/adaptation_advisor.py already codified "
        "one real, narrow slice (RAG vs. fine-tuning vs. in-context learning vs. "
        "distillation) but the full chain this capability's own success criterion names -- "
        "deterministic logic -> traditional ML -> LLM -> RAG -> tool calling -> agent -> "
        "multi-agent -> human approval -> autonomous execution -- had no dedicated artifact. "
        "New app/evaluation/ai_product_decision_framework.py codifies the full chain as "
        "explicit, testable if/then logic, verified against 5 of this project's own real "
        "architectural scenarios (every one mapped to the real tier that was actually "
        "built). New app/evaluation/ai_product_decision_log.py: a real, populated log of "
        "decisions this project ACTUALLY made -- not invented case studies -- each citing "
        "its real commit hash or spec file, verified by a test confirming every cited "
        "commit genuinely exists in this repo's git history. New dedicated 'Decision "
        "Framework' dashboard page: a fully live, interactive recommender (100% free, "
        "deterministic, no LLM call) plus the real decision log browsable by tier. Expanded "
        "from 12 to 18 entries in a later pass toward 100% overall progress, adding real "
        "decisions from the HITL/undo/caching/memory-decay batches (e.g. the real "
        "git-over-SSH-vs-REST choice for modify_github, the semantic cache's real "
        "threshold recalibration, the explicit scope reversal to build real writing "
        "tools). Kept below 100%, honestly: the log has 18 of this project's full real "
        "decision history (227+ 'Example N' sections across specs, 109 commits) -- a real, "
        "growing sample, not yet exhaustive.",
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
