"""Mermaid source for the system architecture diagram shown on the
dashboard's Architecture page.

Every box/edge here traces to real code, verified by reading it directly
(not inferred from names or specs) while answering the user's specific
questions about routing, tools, retrieval, memory, goals, and Chief of
Staff.

HISTORY:
1. This diagram originally showed two SEPARATE, disconnected routers
   (DomainRouter and TaskClassifier+Orchestrator) -- a real architectural
   gap found while building this page. The user asked for one combined
   router instead. That's now app/routing/unified_router.py's
   UnifiedRouter, used internally by Orchestrator: it classifies domain
   (CAREER/PM/FINANCE/LEARNING/GENERAL) and task-type (RESEARCH/ANALYSIS/
   PLANNING/UNCLEAR) as two stages of one router, then Orchestrator
   injects the classified domain into the dispatched agent's prompt as
   context.
2. This diagram then went stale after a later change: the user pointed
   out "Why would only research agent do tool calling? Even analyst and
   planner can do tool calling?" -- a real gap, since AnalystAgent/
   PlannerAgent were plain single-shot Agent subclasses at the time. All 3
   agents now share one tool set via app/agents/agent_tools.py's
   build_shared_tools() (each is a real ToolAgent with its own per-turn
   call_tool-vs-final_answer decision -- never forced either way), which
   also grew from 5 to 8 tools once analyze_feedback/analyze_jd/draft_prd
   were bridged in (app/tools/domain_workflow_tools.py). This diagram was
   NOT updated when that code changed -- caught by the user noticing the
   deployed diagram still showed the old, narrower picture. Fixed here;
   the lesson (documented so it isn't repeated) is that this diagram is
   hand-maintained prose describing the code, not generated from it, so it
   needs an explicit update pass whenever agent/tool wiring changes.

3. This diagram went stale again after multi-agent orchestration was
   added (user's ask: "some inputs will require all 3... pattern will not
   be sequential, will depend on the input"). A free, no-LLM-call
   heuristic gate (might_need_multiple_agents()) now runs BEFORE the
   router/tool-agent path shown above; only when it's true does a real
   MultiAgentPlanner call decide SEQUENTIAL (each agent's output feeds the
   next) vs PARALLEL (independent, then synthesized) vs SINGLE (falls
   through to the normal path with zero extra cost). Documented here
   explicitly as a standing lesson after being caught stale twice now:
   this diagram is hand-maintained prose, not generated from code --
   check it against app/agents/orchestrator.py and
   app/agents/multi_agent_coordinator.py directly whenever either changes,
   don't assume it's still accurate.

4. Updated in the SAME batch as the code this time (applying the lesson
   above) for MCP (Model Context Protocol) support: the user asked for a
   generic, plug-and-play MCP client tested live against GitHub's real
   MCP server. app/tools/mcp_tool.py's MCPConnection/MCPTool/
   discover_mcp_tools() dynamically wrap ANY MCP server's real tools as
   real Tool instances -- indistinguishable from calculator/retrieve/etc.
   to ToolAgent/ToolRegistry, added to build_shared_tools() exactly like
   every other optional tool dependency.

5. Updated in the SAME batch again for AI Observability (Traces page):
   the user asked for retrieval failures, tool failures, error-rate
   logging with example trace ids, and model-drift signals over time. A
   real bug was found and fixed while building this:
   ToolAgent.run() had no try/except around tool.call() at all, so a
   real ToolError crashed the whole request instead of being recorded --
   now caught, recorded as a failed span, and fed back to the LLM as a
   recoverable turn (an on_tool_error hook mirrors on_tool_call). New
   app/observability/error_analysis.py computes real error rate /
   failure-by-kind / stop-reason counts / failure examples (with real
   trace_ids) purely from stored traces -- nothing fabricated. Real
   failure traces (tool failure recovered from, retrieval miss against a
   real human-labeled ground truth, budget-exhausted) are generated once
   by scripts/generate_failure_traces.py and committed, same pattern as
   example_traces.json. Model drift is tracked by
   scripts/track_eval_drift.py re-running the SAME fixed RAG ground-truth
   fixture (documents/question/labels from generate_rag_examples.py)
   over time, appending each real run to eval_history.json -- shown as a
   real (if initially thin) line chart, with an explicit disclosure when
   there are fewer than 3 points that it isn't a trend yet.

6. Updated in the SAME batch again to define Chief of Staff's actual role
   (the user's own 4-point spec) and build the 2 genuinely new
   capabilities it named: a goal-driven loop
   (app/proactive/goal_run.py's GoalRunner -- a real Goal per input,
   Orchestrator reruns until a real structured completion-check call says
   achieved, a real max-iterations budget is hit, or no progress is
   detected between attempts) and proactive harness feedback
   (app/proactive/harness_feedback.py -- reads REAL signals already in
   this codebase: error_analysis.py's trace failures, eval_history.json's
   drift, GoalRunStore's own run history -- and proposes one
   evidence-cited workflow suggestion, never invented, never
   auto-applied). Real career/finance goals (given directly by the user,
   not fabricated) were also seeded into GoalStore for the first time --
   GoalMonitor/ChiefOfStaffOrchestrator already read every domain, not
   just LEARNING, so no wiring change was needed there, only real data.

7. Updated in the SAME batch again after a full context-engineering
   breakdown (user's ask: "let us first breakdown session memory, user
   memory, long term memory ... how each memory is getting called ...
   after how many turn are we summarizing the session ... context
   window/compression ... ordering of memory"). Checked directly against
   the code, not assumed: Orchestrator.handle() was completely stateless
   (no history param at all); MemoryRetriever (real semantic scoring) and
   MemoryWritePolicy (real write gate) existed, tested, but were NEVER
   called from any live request path -- only naive_relevance.py's
   keyword-overlap stand-in was wired in; ContextBuilder's real
   compression path was dead code (always constructed with
   max_tokens=None on its only real call site); PersonalContextEngine's
   real 4-factor scoring was never called from anywhere;
   VoiceSession.turns was recorded but never actually passed back into
   Orchestrator.handle() despite the class's own docstring claiming
   "conversation continuity." Fixed: new app/conversation/session.py's
   ConversationSession wraps Orchestrator (without changing its
   signature -- every existing stateless caller is unaffected), injects
   real recent-turn history + real semantic memory into each request,
   triggers one real LLM summarization call via a real token-budget
   threshold, and writes memory via the real write-policy gate
   (high-importance candidates queued for real human approval, never
   auto-written). VoiceSession now delegates to it, closing its own
   real bug. Verified live against the real Gemini API: a stated
   name+preference was correctly queued for approval at importance=0.8
   and written only after explicit approval; a second turn measurably
   changed its answer style based on the first turn's real injected
   preference.

8. Updated in the SAME batch again to close the 3 remaining Context
   Engineering gaps the prior breakdown (item 7) identified but didn't
   yet fix: (a) PersonalContextEngine's real scoring wired into every
   ConversationSession turn via the new
   app/conversation/context_selection.py -- real selection, not just
   concatenation, with a test proving a low-relevance item is actually
   excluded under a tight budget; (b) ContextBuilder's real compression
   demonstrated live on a new dedicated dashboard page (an interactive
   slider genuinely drops whole sections under a real max_tokens
   budget); (c) lost_in_middle.py's build_positioned_context() run for
   the first time against the real live Gemini API (200 real filler
   chunks, critical fact at start/middle/end, deterministic correctness
   check) -- committed as an honest real finding (no degradation
   observed at this scale for gemini-3.5-flash-lite). New dedicated
   "Context & Memory" dashboard page ties all of this together with its
   own architecture diagram (app/dashboard_ui/context_memory_diagram.py)
   and all 3 experiments live/committed on one page.

9. Updated in the SAME batch again for Model Routing & Model Strategy
   (user's ask: "we are only using gemini for LLM call. what all needs
   to be done to take the progress to 90%"). Checked first, honestly:
   app/routing/model_router.py's ModelRouter/TaskComplexity scaffold
   already existed from Phase 1 -- real, tested -- but its own spec
   (specs/model_routing.md) explicitly said "Not yet wired into
   Orchestrator/main.py"; app/providers/fallback_provider.py's
   FallbackProvider was also real and tested but never used anywhere in
   real code. Fixed: Orchestrator gained an optional agent_llm param
   (classification/planning calls always stay on the cheap tier; the 3
   agents' own generation calls use the routed provider when given).
   New RoutingLLMProvider wraps ModelRouter as a real LLMProvider --
   classifies each request for free (classify_task_complexity(), same
   heuristic pattern as might_need_multiple_agents()), then routes to
   gemini-3.5-flash-lite (cheap) or gemini-3.8-flash (a real, distinct,
   pricier tier with a real 20 requests/day free-tier quota) wrapped in
   a real FallbackProvider. Verified live: while generating the
   committed dashboard examples, the strong tier genuinely hit a real
   503 (external API capacity, consistent with this project's
   documented history) and the real fallback genuinely degraded to the
   cheap tier -- not scripted. New dedicated "Model Routing" dashboard
   page with its own diagram, a live classification demo, and the real
   committed routing examples.

10. Updated in the SAME batch again for a dedicated Evals page (user's
    ask: "arch of eval, golden datasets we have + synthetic data + eval
    score + model used for eval score + types of eval done - llm judge,
    human in the loop, deterministic, etc ... feedback from eval score
    and how it gets tied back"). Checked first, honestly: this
    diagram's own EVALDATA node already disclosed the real, central gap
    -- evals/ was "static JSON + .md, no live grading harness."
    app/evaluation/golden.py's run_golden_case() (deterministic) and
    app/evaluation/llm_judge.py's judge_response() (LLM-as-judge) both
    existed, real, tested, but had never been run end-to-end against
    the real, live Orchestrator until new
    scripts/generate_eval_harness_run.py, which ran all 5 real golden
    cases through it. First pass (5 cases) came back 100% pass / 1.00
    judge score -- honest but never demonstrated a real failure, so a
    follow-up (user's ask: "there should be low scoring runs as well on
    the eval dashboard and how the feedback got translated") added 2
    deliberately adversarial cases to evals/golden/basic_routing.json
    for a genuine, non-staged chance at a real low score. One
    genuinely failed deterministically (expected the "retrieve" tool,
    which this harness's Orchestrator never registers -- a real,
    honest limitation of this specific harness configuration).
    app/proactive/harness_feedback.py gained a new, optional
    eval_harness_run evidence parameter, and a real HarnessSuggestion
    was generated citing that exact real failing case -- closing the
    full "feedback tied back" loop end to end with a real score
    producing a real, evidence-cited proposed workflow change (even
    if the LLM's specific diagnosis was imperfect -- disclosed
    honestly on the page, not hidden). New dedicated "Evals" dashboard
    page: its own diagram, live counts of every golden/synthetic
    dataset, a live (free, no LLM call) citation_quality() demo, the
    real committed harness results (including the real low-scoring
    case), the real generated suggestion, and an illustrative (clearly
    labeled, not real-human-rated) human-in-the-loop correlation
    worked example.

11. Updated in the SAME batch again for Production AI Engineering /
    Governance & Guardrails (user's ask: "lets get into production ai
    engineering and establish governance, guardrail ... i'm thinking of
    sandboxes"). Checked first, honestly -- a real, significant gap: a
    real PolicyEngine (classify -> permission check -> approval ->
    execute -> audit) already existed and was tested, but the live
    chat-agent path (ToolAgent, behind Orchestrator -- what every real
    request actually goes through) called tool.call() directly,
    completely bypassing it; only separate domain-workflow code ever
    used PolicyEngine. And no tool call anywhere ran with any real
    process isolation or resource limits. Fixed: new
    app/platform/sandbox.py's SandboxedToolExecutor runs a tool's real
    execution in a genuinely separate OS process
    (multiprocessing.Process(spawn)), with a real, enforced wall-clock
    timeout and a real memory ceiling (resource.RLIMIT_AS) set inside
    the child -- risk-scaled, so a HIGH-risk tool gets the tightest real
    limits. A real, honest platform limitation was found and disclosed,
    not hidden: on macOS (this dev machine), RLIMIT_AS often cannot be
    lowered at all (a real Darwin/XNU kernel limitation) -- every result
    now reports whether the memory limit was actually enforced, rather
    than silently claiming it was. PolicyEngine's own execution step now
    runs through this sandbox. ToolAgent (and Orchestrator) gained a new
    optional policy_engine param -- when given, EVERY real tool call
    from a live chat request goes through real risk classification, real
    sandboxed execution, and a real human-approval gate for WRITE/ACT
    tools (a new StopReason.APPROVAL_PENDING + AgentResponse.pending_action_id
    surface this cleanly). Verified fully live against the real Gemini
    API: a real READ-classified request completed normally through the
    sandbox; the same tool, overridden to ACT, genuinely stopped a real
    chat request mid-flight with a real pending action_id, then
    genuinely executed after a real PolicyEngine.resume_after_approval()
    call; a real slow tool was genuinely killed by the real sandbox
    timeout. New dedicated "Governance & Sandbox" dashboard page: its
    own diagram, a live (free, no LLM call) interactive sandbox demo
    (pick a real delay and timeout, watch a real subprocess get
    terminated or complete), and the 3 real committed governed-chat-request
    examples.

One thing drawn here is still a real gap/simplification, not a modeling
choice, and is labeled as such directly in the diagram: Chief of Staff's
"listening" is a pull-based batch pipeline
(ChiefOfStaffOrchestrator.process(events)) -- it processes a list of events
handed to it by a caller, not an always-on background poller/scheduler
(confirmed: no such scheduler exists in this codebase).
"""

ARCHITECTURE_DIAGRAM = r"""
flowchart TB
    USER["User request\n(CLI / voice / dashboard trace)"]

    HEURISTIC{"might_need_multiple_agents()\nFREE, no LLM call --\nsequencing keyword OR >=18 words?"}
    USER --> HEURISTIC

    HEURISTIC -->|"no (most requests)"| DR
    HEURISTIC -->|"yes"| MAPLANNER["MultiAgentPlanner\n1 real LLM call: which agents,\nSEQUENTIAL / PARALLEL / SINGLE?"]

    MAPLANNER -->|SINGLE| DR
    MAPLANNER -->|"SEQUENTIAL or PARALLEL"| COORDINATOR

    subgraph COORDINATOR["MultiAgentCoordinator -- runs Orchestrator's OWN agent instances"]
        direction TB
        SEQ["SEQUENTIAL:\neach agent's real output becomes\ncontext for the next agent's input"]
        PAR["PARALLEL:\nagents run independently on the\nsame input, then 1 LLM call\nsynthesizes their outputs"]
    end

    subgraph UNIFIED["UnifiedRouter -- ONE router, two classification stages"]
        direction LR
        DR["Stage 1: domain\nCAREER / PM / FINANCE / LEARNING / GENERAL\n(reuses DomainRouter's prompt/logic)"]
        TC["Stage 2: task-type\nRESEARCH / ANALYSIS / PLANNING / UNCLEAR\n(reuses TaskClassifier's prompt/logic)"]
        DR --> TC
    end

    TC --> ORCH["Orchestrator\ninjects classified domain as\ncontext into the dispatched agent"]
    MODELROUTE["ModelRouter / RoutingLLMProvider\n(optional agent_llm) -- real per-request\nrouting between gemini tiers,\nsee the dedicated Model Routing page/diagram"]
    ORCH -.->|"agent_llm, when given --\nclassification above always\nstays on the cheap tier"| MODELROUTE
    ORCH -->|RESEARCH| RA["ResearchAgent (ToolAgent)"]
    ORCH -->|ANALYSIS| AA["AnalystAgent (ToolAgent)"]
    ORCH -->|PLANNING| PA["PlannerAgent (ToolAgent)"]
    MODELROUTE -.-> RA

    SEQ -.->|"same 3 agent instances,\nnot rebuilt"| RA
    PAR -.->|"same 3 agent instances,\nnot rebuilt"| RA

    subgraph DECISIONLOOP["Every one of the 3 agents: same per-turn decision, every turn"]
        direction TB
        DEC["LLM sees: system prompt + full tool list +\nconversation history so far + user request"]
        DEC -->|"decides call_tool"| CALLTOOL["Calls one tool, sees its\nreal result, loops again\n(never forced -- LLM's own choice)"]
        DEC -->|"decides final_answer"| DIRECT["Answers directly,\nno tool call at all"]
        CALLTOOL -->|"ToolError raised"| TOOLERR["Caught, recorded as a\nfailed span, fed back to\nthe LLM as a recoverable turn\n(real bug fix -- used to crash)"]
        TOOLERR --> DEC
        CALLTOOL --> DEC
        CALLTOOL -.->|"optional policy_engine --\nreal governance + sandbox,\nsee the dedicated\nGovernance & Sandbox page/diagram"| GOVREF["PolicyEngine + SandboxedToolExecutor"]
    end

    RA --> DECISIONLOOP
    AA --> DECISIONLOOP
    PA --> DECISIONLOOP

    ORCH -.->|"domain label only --\nnot wired to any\ndomain workflow below"| DOMAINDATA["app/domains/{career,pm,finance,learning}/*\ninterview_prep, resume_optimization (retriever-grounded),\nstakeholder_request, analyze_portfolio, evaluate_answer\n(need a real Portfolio/Exercise object a chat\nmessage can't manufacture -- invoked separately)"]

    DECISIONLOOP --> TOOLS

    subgraph TOOLS["Tool Registry -- 8 built-in tools + N live MCP tools, same set for all 3 agents"]
        direction TB
        T1["calculator\n(local, no credentials, always on)"]
        T2["analyze_feedback\n(local, no credentials, always on)"]
        T3["retrieve\n(needs an indexed VectorStore,\ne.g. --index-file)"]
        T4["analyze_jd\n(needs SecureRetriever + requester identity --\nbridges app/domains/career/jd_analysis.py)"]
        T5["draft_prd\n(needs SecureRetriever + requester identity --\nbridges app/domains/pm/prd.py)"]
        T6["calendar_day\n(needs real CalendarClient)"]
        T7["email_summary\n(needs real EmailClient)"]
        T8["github_activity\n(needs real GitHubClient, direct REST API)"]
        T9["mcp_* (N tools)\ndynamically discovered from ANY\nconnected MCP server -- generic,\nnot GitHub-specific code"]
    end

    subgraph MCPLAYER["MCP (Model Context Protocol) -- plug and play, any server"]
        direction TB
        MCPCONN["MCPConnection\npersistent session, background\nasyncio event loop thread"]
        MCPDISCOVER["discover_mcp_tools()\nlist_tools() -> real MCPTool\nper server-advertised tool"]
        MCPCONN --> MCPDISCOVER
        MCPDISCOVER -.->|"tested live against"| GHMCP["GitHub's official remote\nMCP server\n(api.githubcopilot.com/mcp/)"]
    end

    MCPDISCOVER --> T9

    T3 --> VECSTORE["VectorStore (FAISS)\nreal embeddings via\nSentenceTransformerEmbedding"]
    T4 --> SECURERETR["SecureRetriever\n(permission-filtered)"]
    T5 --> SECURERETR
    SECURERETR --> VECSTORE
    DOMAINDATA -.->|"same retrieval pattern,\ncalled directly with real inputs"| SECURERETR

    MEMSTORE["PersistentMemoryStore\n(SQLite)"]
    NAIVEREL["naive_relevance.py\nkeyword overlap ONLY --\nNOT semantic search\n(still used by trace_request.py's\nstateless CLI path)"]
    NAIVEREL --> MEMSTORE

    subgraph CONVSESSION["ConversationSession -- real, stateful, wraps Orchestrator"]
        direction TB
        CSHISTORY["Real turn history\n+ running summary"]
        CSBUDGET{"History over\ntoken budget?"}
        CSSUMMARY["1 real LLM call:\nsummarize older turns"]
        CSHISTORY --> CSBUDGET
        CSBUDGET -->|yes| CSSUMMARY --> CSHISTORY
    end
    CTXSELECT["PersonalContextEngine\nreal selection under a real token\nbudget -- see the dedicated\nContext & Memory page/diagram"]
    CONVSESSION --> CTXSELECT
    CTXSELECT -.->|"selected items only --\nsee context_memory_diagram.py"| ORCH
    MEMRETRIEVER["MemoryRetriever\nreal 4-factor semantic scoring:\nsimilarity/recency/importance/confirmed"]
    MEMRETRIEVER --> MEMSTORE
    CONVSESSION --> MEMRETRIEVER
    MEMRETRIEVER --> CTXSELECT

    WRITEPOLICY["MemoryWritePolicy\nclassify -> importance threshold ->\nduplicate check -> approval gate"]
    CONVSESSION -->|"after every turn"| WRITEPOLICY
    WRITEPOLICY -->|"low importance"| MEMSTORE
    WRITEPOLICY -->|"high importance"| PENDINGAPPROVAL["Pending human approval\n(never auto-written)"]
    PENDINGAPPROVAL -->|"approved"| MEMSTORE

    VOICESESSION["VoiceSession\n(real bug fixed: turns were\nrecorded but never replayed)"]
    VOICESESSION --> CONVSESSION

    GOALSTORE["GoalStore (SQLite)\n15 real learning goals +\nreal career/finance goals\n(given directly by the user)"]
    GOALAGENT["GoalAgent\ntrack / detect conflicts /\ndependencies / priorities"]
    GOALAGENT --> GOALSTORE

    subgraph COS["Chief of Staff -- PULL-based, not always-on"]
        direction TB
        EVENTS["events: list[Event]\n(supplied by a caller --\nno background poller/scheduler exists)"]
        TRIGGERS["TriggerEngine"]
        ATTENTION["AttentionEngine"]
        DECISION["DecisionEngine"]
        EVENTS --> TRIGGERS --> ATTENTION --> DECISION
        DECISION -->|PROPOSE_PLAN| PLANS["action_plans.py\n-> PolicyEngine approval gate"]
    end

    subgraph GOALLOOP["Goal-driven loop (harness engineering) --\nGoalRunner, per real input"]
        direction TB
        GRINPUT["Real input -> a real Goal\n(GoalAgent.track)"]
        GRLOOP["Orchestrator reruns until:\nachieved / max_iterations / no_progress"]
        GRCHECK["GoalCompletionChecker\n1 real structured LLM call per\niteration: achieved? yes/no + why"]
        GRINPUT --> GRLOOP --> GRCHECK
        GRCHECK -->|"not achieved,\nbudget remains"| GRLOOP
    end
    GOALAGENT --> GRINPUT
    GRLOOP -.->|"each iteration\nreruns"| ORCH
    GRSTORE["GoalRunStore (SQLite)\nevery iteration + real stop_reason"]
    GRCHECK --> GRSTORE

    HARNESSFEED["harness_feedback.py\nreads error_analysis.py +\neval_history.json + GoalRunStore,\nproposes 1 evidence-cited suggestion\n(never auto-applied)"]
    ERRANALYSIS --> HARNESSFEED
    EVALHISTORY --> HARNESSFEED
    GRSTORE --> HARNESSFEED

    EVALDATA["evals/\ncareer, pm, finance, learning,\ncross_domain, golden, adversarial\n(static JSON + .md -- golden/ is now\nreal-harness-graded, see the Evals page/diagram;\ndomain sets still have no live grading harness)"]

    TRACESTORE["TraceStore (SQLite)\ntrace_id = execution_id"]
    DECISIONLOOP -.->|"trace_request.py records\nevery span here"| TRACESTORE
    ORCH -.-> TRACESTORE
    NAIVEREL -.-> TRACESTORE

    ERRANALYSIS["error_analysis.py\nerror rate / failures-by-kind /\nstop reasons / example trace ids\n-- pure computation over TraceStore"]
    TRACESTORE --> ERRANALYSIS

    EVALHISTORY["eval_history.json\nappended by track_eval_drift.py\nrerunning the SAME fixed RAG\nground truth over time"]
    ERRANALYSIS -.->|"shown together on"| TRACESPAGE["Dashboard Traces page:\nError rates & failures +\nModel drift over time"]
    EVALHISTORY --> TRACESPAGE
"""
