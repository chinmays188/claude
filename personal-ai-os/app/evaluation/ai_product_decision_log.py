"""A real, populated log of decisions ACTUALLY MADE in this project, per
the user's framing: "we have already taken lot of decisions in this
project ... build this decision framework as we go along." Not invented
case studies -- every entry below is a real architectural decision this
project genuinely made, with its real rationale pulled directly from the
actual commit/spec that made it (cited by hash or file), tagged with
which real tier of app/evaluation/ai_product_decision_framework.py's
chain it corresponds to.

This is itself a real demonstration of the framework: every entry shows
the SAME shape the framework's ProductDecision does (tier, reasoning,
what was rejected and why) -- the log isn't a separate format bolted on,
it's the framework applied retroactively and honestly to this project's
own real history.
"""

from pydantic import BaseModel

from app.evaluation.ai_product_decision_framework import DecisionTier


class LoggedDecision(BaseModel):
    decision_id: str
    title: str
    tier: DecisionTier
    what_was_chosen: str
    what_was_rejected: str
    real_rationale: str
    source: str  # a real commit hash or specs/*.md file this decision came from


# Real decisions, in roughly chronological order, each citing its real
# source. Pulled directly from this project's own commit history and
# specs/*.md -- not invented.
DECISION_LOG: list[LoggedDecision] = [
    LoggedDecision(
        decision_id="dual_router_to_unified",
        title="Combine two separate routers into one UnifiedRouter",
        tier=DecisionTier.SINGLE_LLM_CALL,
        what_was_chosen="UnifiedRouter: one entry point, two internal classification stages "
                         "(domain, then task-type), reusing DomainRouter/TaskClassifier's own "
                         "prompts.",
        what_was_rejected="Keeping DomainRouter and TaskClassifier as two separate, "
                           "disconnected routers (the actual state found while building the "
                           "Architecture page).",
        real_rationale="A real architectural gap was found by reading the code directly: "
                        "DomainRouter was only ever called by scripts/trace_request.py and "
                        "tests, while production (app/main.py, voice_api.py) used "
                        "TaskClassifier+Orchestrator -- neither ever saw the other's output. "
                        "The user asked for one combined router instead of two.",
        source="2c6b0b1",
    ),
    LoggedDecision(
        decision_id="all_3_agents_get_tools",
        title="Give all 3 agents (not just ResearchAgent) real tool access",
        tier=DecisionTier.TOOL_CALLING,
        what_was_chosen="build_shared_tools() shared across ResearchAgent/AnalystAgent/"
                         "PlannerAgent, each a real ToolAgent with its own per-turn decision "
                         "loop.",
        what_was_rejected="Only ResearchAgent having tool access (the original state) -- "
                           "AnalystAgent/PlannerAgent as plain, single-shot Agent subclasses.",
        real_rationale="The user pointed out a real asymmetry: 'Why would only research "
                        "agent do tool calling? Even analyst and planner can do tool "
                        "calling?' -- e.g. 'compare these two investment options' genuinely "
                        "needs the calculator for real arithmetic, not an LLM guess.",
        source="06ab859",
    ),
    LoggedDecision(
        decision_id="multi_agent_heuristic_gate",
        title="A free heuristic gate before paying for a real multi-agent planning call",
        tier=DecisionTier.MULTI_AGENT,
        what_was_chosen="might_need_multiple_agents() -- a free, no-LLM-call heuristic "
                         "(sequencing keyword or >=18 words) runs before MultiAgentPlanner's "
                         "real LLM call, which only then decides SEQUENTIAL/PARALLEL/SINGLE.",
        what_was_rejected="Always paying for a real MultiAgentPlanner LLM call on every "
                           "single request, including obviously-simple ones.",
        real_rationale="Confirmed directly with the user: paying for an extra real LLM call "
                        "on every request -- even simple ones -- was an unacceptable cost "
                        "increase. Only requests that plausibly need coordination pay for "
                        "the real planning call.",
        source="a248d84",
    ),
    LoggedDecision(
        decision_id="mcp_generic_not_github_specific",
        title="Build a generic, plug-and-play MCP client, not GitHub-specific code",
        tier=DecisionTier.TOOL_CALLING,
        what_was_chosen="app/tools/mcp_tool.py's MCPConnection/discover_mcp_tools() work "
                         "against ANY MCP server -- a dynamic JSON-Schema-to-Pydantic "
                         "converter makes any future server's tools usable with zero new "
                         "code.",
        what_was_rejected="Writing GitHub-specific tool wrappers directly, since GitHub was "
                           "the only real MCP server being tested against at the time.",
        real_rationale="The user's own framing: 'build MCP connection plug n play and test "
                        "it with a MCP connection with my github' -- GitHub was explicitly "
                        "the test case, not the target. Verified live against the real "
                        "GitHub MCP server (45 real tools discovered) to prove the generic "
                        "design actually works, not just in theory.",
        source="f958752",
    ),
    LoggedDecision(
        decision_id="rag_hybrid_live_generation_committed",
        title="Live chunking/search, but pre-generated (not live) generation+eval",
        tier=DecisionTier.RAG,
        what_was_chosen="Chunking/embedding/search run live and interactive on the RAG page "
                         "(free, local, no LLM call); generation + LLM-judge evaluation use "
                         "pre-generated, committed real examples.",
        what_was_rejected="Making the full RAG pipeline (including real Gemini generation "
                           "calls) live on the public dashboard page.",
        real_rationale="Confirmed with the user: generation/evaluation cost a real Gemini "
                        "call per page view, which this dashboard's standing rule "
                        "(never make live LLM calls on page render, for cost/security on "
                        "public Streamlit Cloud) explicitly rules out. The free, local parts "
                        "stay genuinely live.",
        source="b31de8b",
    ),
    LoggedDecision(
        decision_id="live_retrieval_eval_via_checkboxes",
        title="Real-time recall/precision via user-labeled checkboxes, not a canned example",
        tier=DecisionTier.RAG,
        what_was_chosen="Every live chunk gets a real checkbox ('relevant to this query?'); "
                         "once labeled, evaluate_retrieval() computes real recall/precision "
                         "against the user's own real labels.",
        what_was_rejected="A single pre-generated retrieval-eval example as the only "
                           "evaluation shown.",
        real_rationale="The real blocker for live eval wasn't LLM cost -- recall/precision "
                        "need a human-labeled ground truth, which has nothing to do with "
                        "an LLM call. Solved by having the user label ground truth directly, "
                        "live, with zero API cost.",
        source="6ec72ad",
    ),
    LoggedDecision(
        decision_id="model_routing_second_gemini_tier",
        title="A second Gemini tier for routing, not a new vendor",
        tier=DecisionTier.SINGLE_LLM_CALL,
        what_was_chosen="RoutingLLMProvider routes between gemini-3.5-flash-lite (cheap) and "
                         "gemini-3.8-flash (a real, distinct, pricier tier with a real 20/day "
                         "quota), wrapped in a real FallbackProvider.",
        what_was_rejected="A third-party provider (OpenAI/Anthropic) for genuine cross-vendor "
                           "fallback, or a local Ollama model for the 'free/open-source' "
                           "criterion.",
        real_rationale="Explicitly confirmed with the user: no new API key, no new billing "
                        "this round -- a second Gemini tier demonstrates real tier-based "
                        "routing and a real fallback trigger (the strong tier's real daily "
                        "quota) with zero new cost. The free/open-source criterion was "
                        "explicitly deferred, not silently dropped.",
        source="7e0908c",
    ),
    LoggedDecision(
        decision_id="sandbox_subprocess_not_docker",
        title="Real process-level sandboxing (subprocess), not Docker, for tool execution",
        tier=DecisionTier.TOOL_CALLING,
        what_was_chosen="SandboxedToolExecutor: multiprocessing.Process(spawn) with a real "
                         "wall-clock timeout and a real memory ceiling (resource.RLIMIT_AS).",
        what_was_rejected="Running tool execution inside a real Docker container for "
                           "isolation.",
        real_rationale="Confirmed with the user: subprocess-level sandboxing closes the real "
                        "gap (tools ran completely unsandboxed in-process) and is runnable/"
                        "testable without Docker needing to be available in this "
                        "environment -- Docker itself remained a separate, still-open gap, "
                        "disclosed honestly rather than conflated with this fix.",
        source="e9e5a04",
    ),
    LoggedDecision(
        decision_id="governance_wired_into_tool_agent",
        title="Wire real PolicyEngine governance into the live chat-agent path, not just domain workflows",
        tier=DecisionTier.HUMAN_APPROVAL_REQUIRED,
        what_was_chosen="ToolAgent gained an optional policy_engine param -- when given, "
                         "every real tool call goes through real risk classification, real "
                         "sandboxing, and a real human-approval gate for WRITE/ACT tools.",
        what_was_rejected="Leaving PolicyEngine as a separate, real, tested-but-unused "
                           "component that only domain-workflow code happened to call.",
        real_rationale="A real, previously undisclosed gap found while scoping this work: "
                        "ToolAgent -- what every real chat request actually goes through -- "
                        "called tool.call() directly, completely bypassing PolicyEngine. "
                        "Confirmed with the user this should be fixed this round, not left "
                        "as a separate, unused subsystem.",
        source="e9e5a04",
    ),
    LoggedDecision(
        decision_id="eval_harness_real_adversarial_cases",
        title="Add real adversarial golden cases rather than report a suspiciously clean 100%",
        tier=DecisionTier.SINGLE_LLM_CALL,
        what_was_chosen="2 deliberately hard cases added to evals/golden/basic_routing.json "
                         "(each with a real, documented reason it was expected to be hard), "
                         "for a genuine, non-staged chance at a real low score.",
        what_was_rejected="Reporting the first run's real 100% pass rate / 1.00 judge score "
                           "as the finished result.",
        real_rationale="The user directly asked: 'there should be low scoring runs as well "
                        "on the eval dashboard and how the feedback got translated.' A "
                        "100%-passing harness never demonstrates what a real failure -- or a "
                        "real feedback loop closing on one -- actually looks like.",
        source="828e604",
    ),
    LoggedDecision(
        decision_id="multimodal_gemini_audio_not_whisper",
        title="Gemini native audio understanding for voice STT, not self-hosted Whisper or a paid vendor",
        tier=DecisionTier.SINGLE_LLM_CALL,
        what_was_chosen="GeminiMultimodalProvider.understand() with MediaType.AUDIO -- one "
                         "real Gemini call, same existing free-tier API key this project "
                         "already uses everywhere.",
        what_was_rejected="Self-hosted Whisper (a new real dependency + local compute) or a "
                           "third-party STT vendor (Deepgram/AssemblyAI/ElevenLabs -- real "
                           "cost, a new API key).",
        real_rationale="The user explicitly asked which voice API to integrate 'free of "
                        "cost.' Gemini audio understanding is genuinely $0 marginal cost "
                        "(reuses existing quota), needs no new dependency, and works on real "
                        "uploaded audio files server-side -- confirmed as the chosen option "
                        "before building.",
        source="d022635",
    ),
    LoggedDecision(
        decision_id="multimodal_orchestrator_wraps_not_changes_core",
        title="A new MultimodalOrchestrator wrapper, not a change to Orchestrator's core contract",
        tier=DecisionTier.AGENT,
        what_was_chosen="MultimodalOrchestrator converts image/PDF/audio to real text, then "
                         "hands it to the real, UNCHANGED Orchestrator.handle(text).",
        what_was_rejected="Changing Orchestrator.handle() itself to accept multimodal input "
                           "directly.",
        real_rationale="Confirmed with the user: a deeper change to the core request path "
                        "every existing caller depends on is higher risk for a benefit "
                        "(direct multimodal-in-the-loop) this project doesn't currently "
                        "need. Keeping Orchestrator's contract simple (still just text) "
                        "means every existing, already-tested routing/tool-calling path is "
                        "completely unaffected.",
        source="d022635",
    ),
    LoggedDecision(
        decision_id="fix_fake_parallel_not_rebuild_coordinator",
        title="Fix MultiAgentCoordinator's real concurrency bug in place, don't redesign it",
        tier=DecisionTier.MULTI_AGENT,
        what_was_chosen="ThreadPoolExecutor.map() inside the existing _run_parallel() method, "
                         "same plan.agents ordering preserved.",
        what_was_rejected="A broader redesign of multi-agent coordination (e.g. async/await "
                           "throughout, a new orchestration layer).",
        real_rationale="Found while investigating 'AI Cost & Latency Engineering': "
                        "_run_parallel() was a plain sequential list comprehension despite its "
                        "name -- a real, narrow bug, not a design flaw. The minimal real fix "
                        "(swap the comprehension for ThreadPoolExecutor.map()) closes it "
                        "without touching the already-tested planning/synthesis logic around it.",
        source="1aa5502",
    ),
    LoggedDecision(
        decision_id="semantic_cache_real_threshold_not_fake_threshold",
        title="Re-measure the semantic cache's similarity threshold against the real model",
        tier=DecisionTier.RAG,
        what_was_chosen="A real, re-measured threshold (0.85) and real example questions, "
                         "chosen because their real cosine-similarity scores against the "
                         "actual all-MiniLM-L6-v2 model clearly separate paraphrase from "
                         "unrelated.",
        what_was_rejected="Trusting the existing unit tests' threshold (0.9-0.92), which only "
                           "passed because of a FAKE embedding that hand-picked a 0.98 score "
                           "for one specific pair.",
        real_rationale="Running the real cache live surfaced a real, measured gap: the real "
                        "model scored that exact pair at only 0.089. Shipping the fake's "
                        "threshold would have shipped a semantic cache that almost never hits "
                        "in practice -- caught by actually running it against the real model "
                        "before committing, not by trusting the test suite's green checkmark.",
        source="1268aa4",
    ),
    LoggedDecision(
        decision_id="hitl_approval_queue_reuses_real_audit_log",
        title="A live approval queue reads/writes the SAME real AuditLog, not a separate demo store",
        tier=DecisionTier.HUMAN_APPROVAL_REQUIRED,
        what_was_chosen="The Governance page's new interactive section calls the real "
                         "PolicyEngine against stores['audit'] -- the identical persistent "
                         "AuditLog the rest of the dashboard already reads.",
        what_was_rejected="A separate, isolated in-memory PolicyEngine/AuditLog just for the "
                           "demo, disconnected from the real data every other page shows.",
        real_rationale="A demo approval queue over fake data would not actually demonstrate "
                        "bounded autonomy -- it would just be a UI mockup. Using the real "
                        "store means a real pending action a human approves here is the exact "
                        "same real record every other page's audit trail shows.",
        source="87e9aa0",
    ),
    LoggedDecision(
        decision_id="reverse_read_only_scope_for_real_undo",
        title="Explicitly reverse the calendar/email/GitHub read-only scope decisions",
        tier=DecisionTier.HUMAN_APPROVAL_REQUIRED,
        what_was_chosen="6 new real, undoable writing tools, reversing Sections 24/25's "
                         "earlier 'read-only first' decisions for CalendarClient/EmailClient.",
        what_was_rejected="Leaving every tool read-only and declaring undo/recovery "
                           "structurally out of scope for this project.",
        real_rationale="Scoping undo honestly surfaced a deeper real gap: there was no "
                        "writing action anywhere to attach undo to. The user explicitly chose "
                        "to reverse scope rather than leave the capability's named success "
                        "criterion (undo/recovery) permanently unmet -- a real product "
                        "tradeoff made in the open, not silently.",
        source="78e75dd",
    ),
    LoggedDecision(
        decision_id="github_write_via_ssh_not_rest",
        title="modify_github writes via real git-over-SSH, not the GitHub REST API",
        tier=DecisionTier.TOOL_CALLING,
        what_was_chosen="A new GitHubGitWriteClient pushing a real branch+commit over SSH, "
                         "then deleting it for undo.",
        what_was_rejected="GitHubClient's existing REST-API pattern (Bearer token + "
                           "httpx), which every other GitHub read in this project uses.",
        real_rationale="A real, discovered constraint, not a preference: no GITHUB_TOKEN/"
                        "GH_TOKEN is configured in this environment, so REST-based writes "
                        "(e.g. creating an issue) were not actually possible. SSH push access "
                        "to the real scratch repo WAS confirmed live (git ls-remote "
                        "succeeded) -- the real available credential shaped the real "
                        "implementation choice.",
        source="78e75dd",
    ),
    LoggedDecision(
        decision_id="memory_decay_never_auto_deletes",
        title="Memory decay flags for human review -- it never deletes anything itself",
        tier=DecisionTier.HUMAN_APPROVAL_REQUIRED,
        what_was_chosen="apply_decay()/find_decay_candidates() lower confidence and surface "
                         "low-confidence memories for review; no function anywhere deletes a "
                         "memory for being stale.",
        what_was_rejected="Auto-archiving or auto-deleting memories once their decayed "
                           "confidence drops below a threshold.",
        real_rationale="Matches this project's own standing human-in-the-loop principle "
                        "(the same reason MemoryWritePolicy queues high-importance writes for "
                        "approval instead of auto-writing them) -- a memory being old is a "
                        "signal worth surfacing to a human, not grounds for the system to "
                        "silently decide it's wrong and remove it.",
        source="dfeb467",
    ),
    LoggedDecision(
        decision_id="scale_down_default_governance_not_full_policy_engine",
        title="Scale a 'make it the real default' ask down to a smaller, safer real upgrade",
        tier=DecisionTier.HUMAN_APPROVAL_REQUIRED,
        what_was_chosen="ToolAgent runs every tool call through a real SandboxedToolExecutor "
                         "by default (process isolation, real timeout/memory ceiling).",
        what_was_rejected="Making full PolicyEngine (risk classification + approval gate + "
                           "audit log) the real default for every Orchestrator/ToolAgent caller.",
        real_rationale="Investigating the ask surfaced real blockers: no safe default exists "
                        "for 'which permissions are granted,' and an in-memory default "
                        "AuditLog would be silently discarded, defeating the audit trail's "
                        "purpose. Rather than force a risky change through, scoped down to "
                        "the real, smaller safety upgrade that was actually safe to default.",
        source="c094ca2",
    ),
    LoggedDecision(
        decision_id="cache_wired_into_classification_not_agent_generation",
        title="Wire the real semantic cache into classification calls, not agent generation",
        tier=DecisionTier.RAG,
        what_was_chosen="A new Orchestrator classification_llm param lets UnifiedRouter/"
                         "MultiAgentPlanner's calls use a cache-wrapped provider.",
        what_was_rejected="Wiring the cache into agent_llm (the 3 agents' own generation "
                           "calls), the more obvious integration point.",
        real_rationale="ToolAgent's own generate() embeds an ever-growing conversation "
                        "history + tool-decision JSON each turn -- a real, measured fact that "
                        "makes a cache hit there unrealistic in practice. Classification calls "
                        "are stateless and fixed-shape, a genuinely good fit instead.",
        source="c094ca2",
    ),
    LoggedDecision(
        decision_id="slo_monitor_mirrors_cost_governor_never_blocks",
        title="A real SLO monitor that only signals, never blocks a request itself",
        tier=DecisionTier.HUMAN_APPROVAL_REQUIRED,
        what_was_chosen="SLOMonitor.check() returns a real OK/WARNING/BREACHED alert; no "
                         "caller path is forced to refuse a request based on it.",
        what_was_rejected="Having the monitor itself gate or refuse requests once a "
                           "threshold is breached.",
        real_rationale="Mirrors CostGovernor's own earlier, already-adopted design exactly -- "
                        "a real precedent in this project for 'after-the-fact reporting -> "
                        "alerting signal,' not an automatic enforcement action a human hasn't "
                        "reviewed.",
        source="4d30b50",
    ),
    LoggedDecision(
        decision_id="reranking_after_permission_filter_not_before",
        title="Rerank only already-permission-filtered chunks, never before filtering",
        tier=DecisionTier.RAG,
        what_was_chosen="SecureRetriever's real order: hybrid search -> permission filter -> "
                         "rerank -> top_k.",
        what_was_rejected="Reranking the full candidate set before permission filtering (then "
                           "filtering the reranked results).",
        real_rationale="A denied chunk must never reach the reranker at all -- reranking "
                        "candidates the requester can't see would leak ordering information "
                        "about content outside their access, a real security property, not "
                        "just a performance detail. Proven by a dedicated test.",
        source="2d3821a",
    ),
    LoggedDecision(
        decision_id="tool_retry_only_on_sandbox_violation",
        title="Retry a real transient sandbox failure, never a deterministic tool error",
        tier=DecisionTier.TOOL_CALLING,
        what_was_chosen="ToolAgent retries only SandboxViolation (timeout/crash) for "
                         "retry_safe tools, with real exponential backoff.",
        what_was_rejected="Reusing retry_with_backoff()'s own generic except Exception "
                           "directly, which would also retry a deterministic ToolError.",
        real_rationale="A deterministic failure (e.g. bad arguments) will fail identically "
                        "again -- retrying it only wastes real time and real sandbox "
                        "overhead. Only a genuinely transient signal deserves a real retry.",
        source="dc5f472",
    ),
    LoggedDecision(
        decision_id="finance_scenario_case_needs_zero_llm_calls",
        title="Let a golden case's grading honestly need zero LLM calls when the real code does",
        tier=DecisionTier.DETERMINISTIC_LOGIC,
        what_was_chosen="finance_golden_runner.py's scenario_analysis case calls the real "
                         "analyze_scenario() (no llm parameter at all) and grades the "
                         "deterministic result -- no Gemini call for that case.",
        what_was_rejected="Forcing every domain golden case through a live LLM call for "
                           "uniformity, even when the real workflow being tested doesn't use one.",
        real_rationale="Section 24's own absolute rule for this workflow is that an LLM must "
                        "never compute or restate a scenario shock's numbers. A harness that "
                        "pretended otherwise, or added an unnecessary LLM call just to make "
                        "every case look the same, would misrepresent what the real code "
                        "actually does.",
        source="c7ecf16",
    ),
]


def get_decision(decision_id: str) -> LoggedDecision | None:
    return next((d for d in DECISION_LOG if d.decision_id == decision_id), None)


def decisions_by_tier(tier: DecisionTier) -> list[LoggedDecision]:
    return [d for d in DECISION_LOG if d.tier == tier]


def tier_distribution() -> dict[str, int]:
    """Real count of how many logged decisions landed at each real tier --
    answers 'what tier does this project actually operate at, in
    practice' with real counts, not an assertion."""
    counts: dict[str, int] = {}
    for decision in DECISION_LOG:
        counts[decision.tier.value] = counts.get(decision.tier.value, 0) + 1
    return counts
