"""Mermaid source for the Model Routing & Model Strategy page's dedicated
architecture diagram. Every box/edge traces to real code, verified by
reading it directly.

Built for the user's ask: "we are only using gemini for LLM call. what
all needs to be done to take the progress to 90%." Checked first,
honestly: app/routing/model_router.py's ModelRouter/TaskComplexity was
real, tested, but its own spec (specs/model_routing.md) explicitly said
"Not yet wired into Orchestrator/main.py" -- this diagram shows that
wiring, finally done.
"""

MODEL_ROUTING_DIAGRAM = r"""
flowchart TB
    REQUEST["Agent generation request\n(Orchestrator's agent_llm)"]

    HEURISTIC{"classify_task_complexity()\nFREE, no LLM call --\nsignal phrase OR >=30 words?"}
    REQUEST --> HEURISTIC

    HEURISTIC -->|SIMPLE| CHEAP["gemini-3.5-flash-lite\n(this project's existing default)"]
    HEURISTIC -->|COMPLEX| STRONGATTEMPT["gemini-3.8-flash\n(real, distinct, stronger tier --\nreal hard free-tier quota:\n20 requests/day)"]

    STRONGATTEMPT -->|success| STRONGOK["Served by strong tier\ndegraded=false"]
    STRONGATTEMPT -->|"real failure\n(quota exhausted / 5xx)"| FALLBACK["FallbackProvider\nreal, tested, previously\nnever used anywhere"]
    FALLBACK --> CHEAP2["gemini-3.5-flash-lite\ndegraded=true, real reason recorded"]

    CHEAP --> RESULT["RoutingDecision\n(complexity, model_name,\ndegraded, reason) --\ninspectable, not just the answer"]
    STRONGOK --> RESULT
    CHEAP2 --> RESULT

    RESULT -.->|"one plain string out --\nAgent/ToolAgent unaffected"| AGENT["ResearchAgent / AnalystAgent /\nPlannerAgent (ToolAgent)"]

    ORCHNOTE["Orchestrator's classification/planning\ncalls (UnifiedRouter, MultiAgentPlanner)\nalways use the main llm, NEVER routed --\nclassification never benefits from a\nstronger model and shouldn't spend the\nstrong tier's scarce daily quota"]
    ORCHNOTE -.-> REQUEST
"""
