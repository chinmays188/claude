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

    subgraph UNIFIED["UnifiedRouter -- ONE router, two classification stages"]
        direction LR
        DR["Stage 1: domain\nCAREER / PM / FINANCE / LEARNING / GENERAL\n(reuses DomainRouter's prompt/logic)"]
        TC["Stage 2: task-type\nRESEARCH / ANALYSIS / PLANNING / UNCLEAR\n(reuses TaskClassifier's prompt/logic)"]
        DR --> TC
    end

    USER --> DR

    TC --> ORCH["Orchestrator\ninjects classified domain as\ncontext into the dispatched agent"]
    ORCH -->|RESEARCH| RA["ResearchAgent (ToolAgent)"]
    ORCH -->|ANALYSIS| AA["AnalystAgent (ToolAgent)"]
    ORCH -->|PLANNING| PA["PlannerAgent (ToolAgent)"]

    subgraph DECISIONLOOP["Every one of the 3 agents: same per-turn decision, every turn"]
        direction TB
        DEC["LLM sees: system prompt + full tool list +\nconversation history so far + user request"]
        DEC -->|"decides call_tool"| CALLTOOL["Calls one tool, sees its\nreal result, loops again\n(never forced -- LLM's own choice)"]
        DEC -->|"decides final_answer"| DIRECT["Answers directly,\nno tool call at all"]
        CALLTOOL --> DEC
    end

    RA --> DECISIONLOOP
    AA --> DECISIONLOOP
    PA --> DECISIONLOOP

    ORCH -.->|"domain label only --\nnot wired to any\ndomain workflow below"| DOMAINDATA["app/domains/{career,pm,finance,learning}/*\ninterview_prep, resume_optimization (retriever-grounded),\nstakeholder_request, analyze_portfolio, evaluate_answer\n(need a real Portfolio/Exercise object a chat\nmessage can't manufacture -- invoked separately)"]

    DECISIONLOOP --> TOOLS

    subgraph TOOLS["Tool Registry -- ALL 8 real tools, same set for all 3 agents"]
        direction TB
        T1["calculator\n(local, no credentials, always on)"]
        T2["analyze_feedback\n(local, no credentials, always on)"]
        T3["retrieve\n(needs an indexed VectorStore,\ne.g. --index-file)"]
        T4["analyze_jd\n(needs SecureRetriever + requester identity --\nbridges app/domains/career/jd_analysis.py)"]
        T5["draft_prd\n(needs SecureRetriever + requester identity --\nbridges app/domains/pm/prd.py)"]
        T6["calendar_day\n(needs real CalendarClient)"]
        T7["email_summary\n(needs real EmailClient)"]
        T8["github_activity\n(needs real GitHubClient)"]
    end

    T3 --> VECSTORE["VectorStore (FAISS)\nreal embeddings via\nSentenceTransformerEmbedding"]
    T4 --> SECURERETR["SecureRetriever\n(permission-filtered)"]
    T5 --> SECURERETR
    SECURERETR --> VECSTORE
    DOMAINDATA -.->|"same retrieval pattern,\ncalled directly with real inputs"| SECURERETR

    MEMSTORE["PersistentMemoryStore\n(SQLite)"]
    NAIVEREL["naive_relevance.py\nkeyword overlap ONLY --\nNOT semantic search"]
    NAIVEREL --> MEMSTORE

    GOALSTORE["GoalStore (SQLite)\n15 real user learning goals"]
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

    EVALDATA["evals/\ncareer, pm, finance, learning,\ncross_domain, golden, adversarial\n(static JSON + .md, no live grading harness)"]

    TRACESTORE["TraceStore (SQLite)\ntrace_id = execution_id"]
    DECISIONLOOP -.->|"trace_request.py records\nevery span here"| TRACESTORE
    ORCH -.-> TRACESTORE
    NAIVEREL -.-> TRACESTORE
"""
