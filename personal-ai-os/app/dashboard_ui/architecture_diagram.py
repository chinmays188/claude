"""Mermaid source for the system architecture diagram shown on the
dashboard's Architecture page.

Every box/edge here traces to real code, verified by reading it directly
(not inferred from names or specs) while answering the user's specific
questions about routing, tools, retrieval, memory, goals, and Chief of
Staff. Two things drawn here are real gaps/simplifications, not modeling
choices, and are labeled as such directly in the diagram:

1. DomainRouter and TaskClassifier+Orchestrator are two SEPARATE,
   independent entry points -- neither calls the other, nothing combines
   their outputs. app/main.py and app/api/voice_api.py use Orchestrator;
   nothing in production uses DomainRouter (only scripts/trace_request.py
   and tests do).
2. Chief of Staff's "listening" is a pull-based batch pipeline
   (ChiefOfStaffOrchestrator.process(events)) -- it processes a list of
   events handed to it by a caller, not an always-on background
   poller/scheduler (confirmed: no such scheduler exists in this codebase).
"""

ARCHITECTURE_DIAGRAM = r"""
flowchart TB
    USER["User request\n(CLI / voice / dashboard trace)"]

    subgraph ROUTERS["⚠️ Two SEPARATE, disconnected routers -- neither calls the other"]
        direction LR
        DR["DomainRouter\nCAREER / PM / FINANCE / LEARNING / UNCLEAR\n(used by: scripts/trace_request.py, tests only)"]
        TC["TaskClassifier\nRESEARCH / ANALYSIS / PLANNING / UNCLEAR\n(used by: app/main.py, app/api/voice_api.py)"]
    end

    USER --> DR
    USER --> TC

    TC --> ORCH["Orchestrator"]
    ORCH -->|RESEARCH| RA["ResearchAgent\n(ToolAgent)"]
    ORCH -->|ANALYSIS| AA["AnalystAgent\n(single-shot)"]
    ORCH -->|PLANNING| PA["PlannerAgent\n(single-shot)"]

    DR -.->|"domain label only --\nnot wired to any agent\nin production"| DOMAINDATA["app/domains/{career,pm,finance,learning}/*\nJD analysis, resume optimization,\nstakeholder requests, PRDs, etc."]

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
    DR -.-> TRACESTORE
    ORCH -.-> TRACESTORE
    NAIVEREL -.-> TRACESTORE
"""
