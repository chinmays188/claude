"""Mermaid source for the system architecture diagram shown on the
dashboard's Architecture page.

Every box/edge here traces to real code, verified by reading it directly
(not inferred from names or specs) while answering the user's specific
questions about routing, tools, retrieval, memory, goals, and Chief of
Staff.

HISTORY: this diagram originally showed two SEPARATE, disconnected routers
(DomainRouter and TaskClassifier+Orchestrator) -- a real architectural gap
found while building this page. The user asked for one combined router
instead. That's now app/routing/unified_router.py's UnifiedRouter, used
internally by Orchestrator: it classifies domain (CAREER/PM/FINANCE/
LEARNING/GENERAL) and task-type (RESEARCH/ANALYSIS/PLANNING/UNCLEAR) as two
stages of one router, then Orchestrator injects the classified domain into
the dispatched agent's prompt as context. This diagram reflects that fix.

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
    ORCH -->|RESEARCH| RA["ResearchAgent\n(ToolAgent)"]
    ORCH -->|ANALYSIS| AA["AnalystAgent\n(single-shot, domain-aware)"]
    ORCH -->|PLANNING| PA["PlannerAgent\n(single-shot, domain-aware)"]

    ORCH -.->|"domain label only --\nnot wired to any\ndomain workflow below"| DOMAINDATA["app/domains/{career,pm,finance,learning}/*\nJD analysis, resume optimization,\nstakeholder requests, PRDs, etc.\n(need typed inputs a chat message\ndoesn't provide -- invoked separately)"]

    RA --> TOOLS

    subgraph TOOLS["Tool Registry (5 real tools)"]
        direction TB
        T1["calculator\n(local, no credentials)"]
        T2["retrieve\n(local FAISS + embeddings,\nno credentials)"]
        T3["calendar_day\n(needs real CalendarClient)"]
        T4["email_summary\n(needs real EmailClient)"]
        T5["github_activity\n(needs real GitHubClient)"]
    end

    T2 --> VECSTORE["VectorStore (FAISS)\nreal embeddings via\nSentenceTransformerEmbedding"]
    DOMAINDATA -->|"resume_optimization,\ninterview_prep, jd_analysis,\nprd, stakeholder_request"| SECURERETR["SecureRetriever\n(permission-filtered)"]
    SECURERETR --> VECSTORE

    MEMSTORE["PersistentMemoryStore\n(SQLite)"]
    NAIVEREL["naive_relevance.py\nkeyword overlap ONLY --\nNOT semantic search"]
    NAIVEREL --> MEMSTORE

    GOALSTORE["GoalStore (SQLite)"]
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
    RA -.->|"trace_request.py records\nevery span here"| TRACESTORE
    ORCH -.-> TRACESTORE
    NAIVEREL -.-> TRACESTORE
"""
