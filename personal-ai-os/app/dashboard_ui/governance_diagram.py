"""Mermaid source for the Production AI Engineering / Governance &
Guardrails page's dedicated architecture diagram. Every box/edge traces
to real code, verified by reading it directly.

Built for the user's ask: "lets get into production ai engineering and
establish governance, guardrail ... i'm thinking of sandboxes."

Checked first, honestly: a real governance layer (PolicyEngine: classify
-> permission check -> approval -> execute -> audit) already existed and
was tested -- but the live chat-agent path (ToolAgent, behind
Orchestrator -- what every real request actually goes through) called
tool.call() directly, completely bypassing it; only separate
domain-workflow code ever used PolicyEngine. And no tool call anywhere
ran with any real process isolation or resource limits. This diagram
shows both the real, previously-existing governance pipeline AND the two
real gaps this session closed: the wiring from ToolAgent into
PolicyEngine, and the new, real process-level sandbox.
"""

GOVERNANCE_DIAGRAM = r"""
flowchart TB
    AGENTDECISION["Agent decides to call a tool\n(Research/Analyst/Planner's\nreal ToolAgent decision loop)"]

    HASPOLICY{"policy_engine given?\n(optional, additive --\nunset = old direct\ntool.call(), unsandboxed)"}
    AGENTDECISION --> HASPOLICY
    HASPOLICY -->|"no (legacy path,\nstill default)"| DIRECTCALL["tool.call(args)\n-- direct, in-process,\nno governance, no sandbox"]
    HASPOLICY -->|"yes -- the real fix\nthis session"| PROPOSE["PolicyEngine.propose_and_execute()"]

    subgraph GOVERNANCE["PolicyEngine -- real governance pipeline"]
        direction TB
        CLASSIFY["ActionClassifier.classify()\nREAD / WRITE / ACT\n(real, deterministic mapping\n+ per-tool overrides)"]
        RISK["assess_risk()\nLOW / MEDIUM / HIGH"]
        PERMCHECK["PermissionChecker.check()\nreal, runtime-enforced\n(not just declared on the Tool)"]
        APPROVALGATE{"requires_approval()?\n(READ = no, WRITE/ACT = yes)"}
        CLASSIFY --> RISK --> PERMCHECK --> APPROVALGATE
    end
    PROPOSE --> CLASSIFY

    APPROVALGATE -->|"no"| SANDBOXEXEC
    APPROVALGATE -->|"yes"| PENDING["ApprovalPending raised\n-- real action_id, recorded\nin AuditLog as PENDING"]
    PENDING -.->|"ToolAgent catches this --\nstops the loop, returns\nstop_reason=approval_pending\n+ pending_action_id"| AGENTRESPONSE["AgentResponse\n(real, inspectable)"]

    HUMANAPPROVE["A real human calls\nPolicyEngine.resume_after_approval()\n(approved=True/False)"]
    PENDING -.->|"later, out of band"| HUMANAPPROVE
    HUMANAPPROVE -->|approved| SANDBOXEXEC
    HUMANAPPROVE -->|rejected| REJECTED["Recorded REJECTED,\nnever executed"]

    subgraph SANDBOX["SandboxedToolExecutor -- real process-level isolation (new)"]
        direction TB
        SPAWN["multiprocessing.Process(spawn)\nreal, separate OS process --\nnot a thread, not in-process"]
        MEMLIMIT["resource.setrlimit(RLIMIT_AS, ...)\nset INSIDE the child --\nreal on Linux; a real, disclosed\nlimitation on macOS (can't be\nlowered -- confirmed while\nbuilding this)"]
        TIMEOUT["process.join(timeout) --\nreal wall-clock limit,\nterminate()/kill() if still alive"]
        RISKLIMITS["Limits SCALE with real risk level:\nHIGH tightest (3s/64MB),\nLOW loosest (10s/256MB)"]
        SPAWN --> MEMLIMIT
        SPAWN --> TIMEOUT
        RISKLIMITS -.-> SPAWN
    end
    SANDBOXEXEC["sandbox.execute(tool, args, risk_level)"] --> SPAWN

    TOOLRESULT["Real tool result OR a real\nSandboxViolation (timeout/\ncrash) OR a real ToolError"]
    SPAWN --> TOOLRESULT

    AUDIT["AuditLog -- every proposal,\napproval decision, execution\nresult, and verification\nrecorded, READ included"]
    TOOLRESULT --> AUDIT
    PENDING --> AUDIT
    REJECTED --> AUDIT

    TOOLRESULT -.-> AGENTRESPONSE

    DOCKERNOTE["Separate, different layer:\nDockerfile/docker-compose.yml\n(whole-container isolation,\nnetwork/filesystem jail) --\nNOT what SandboxedToolExecutor\nreplaces; a real, still-open\ngap (never actually built/run\nin this environment)"]
    SANDBOX -.->|"different isolation layer,\nnot a substitute for"| DOCKERNOTE
"""
