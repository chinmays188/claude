"""Mermaid source for the Model Routing & Model Strategy page's dedicated
architecture diagram. Every box/edge traces to real code, verified by
reading it directly.

Built for the user's ask: "we are only using gemini for LLM call. what
all needs to be done to take the progress to 90%." Checked first,
honestly: app/routing/model_router.py's ModelRouter/TaskComplexity was
real, tested, but its own spec (specs/model_routing.md) explicitly said
"Not yet wired into Orchestrator/main.py" -- this diagram shows that
wiring, finally done.

Updated for the user's follow-up ask: "lets install ollama and get into
model routing." The SIMPLE path previously went straight to
gemini-3.5-flash-lite -- both tiers were still the same vendor (Gemini),
a real, disclosed gap this capability's own success criteria named
("when free/open-source models are the right choice"). Closed: real
Ollama installed locally (brew services, v0.40.2), a real local model
pulled (llama3.2:1b, 1.3GB), and app/providers/ollama_provider.py wraps
Ollama's local HTTP API as a genuine LLMProvider -- no API key, no
network call, zero cost, zero quota. RoutingLLMProvider's SIMPLE path
now tries this real local tier FIRST via FallbackProvider(ollama,
cheap_gemini), degrading to the existing cheap Gemini tier if Ollama
isn't running -- the same resilience pattern already proven for the
COMPLEX/strong tier below.
"""

MODEL_ROUTING_DIAGRAM = r"""
flowchart TB
    REQUEST["Agent generation request\n(Orchestrator's agent_llm)"]

    HEURISTIC{"classify_task_complexity()\nFREE, no LLM call --\nsignal phrase OR >=30 words?"}
    REQUEST --> HEURISTIC

    HEURISTIC -->|SIMPLE| LOCALATTEMPT["ollama/llama3.2:1b\n(real, local, free -- no API key,\nno network call, zero quota --\nvia Ollama's local HTTP API)"]
    HEURISTIC -->|COMPLEX| STRONGATTEMPT["gemini-3.8-flash\n(real, distinct, stronger tier --\nreal hard free-tier quota:\n20 requests/day)"]

    LOCALATTEMPT -->|success| LOCALOK["Served by free local tier\ndegraded=false"]
    LOCALATTEMPT -->|"real failure\n(Ollama not running)"| LOCALFALLBACK["FallbackProvider\n(local, cheap) -- same resilience\npattern as the strong tier below"]
    LOCALFALLBACK --> CHEAP["gemini-3.5-flash-lite\ndegraded=true, real reason recorded"]

    STRONGATTEMPT -->|success| STRONGOK["Served by strong tier\ndegraded=false"]
    STRONGATTEMPT -->|"real failure\n(quota exhausted / 5xx)"| FALLBACK["FallbackProvider\n(strong, cheap)"]
    FALLBACK --> CHEAP2["gemini-3.5-flash-lite\ndegraded=true, real reason recorded"]

    LOCALOK --> RESULT["RoutingDecision\n(complexity, model_name,\ndegraded, reason) --\ninspectable, not just the answer"]
    CHEAP --> RESULT
    STRONGOK --> RESULT
    CHEAP2 --> RESULT

    RESULT -.->|"one plain string out --\nAgent/ToolAgent unaffected"| AGENT["ResearchAgent / AnalystAgent /\nPlannerAgent (ToolAgent)"]

    ORCHNOTE["Orchestrator's classification/planning\ncalls (UnifiedRouter, MultiAgentPlanner)\nalways use the main llm, NEVER routed --\nclassification never benefits from a\nstronger model and shouldn't spend the\nstrong tier's scarce daily quota"]
    ORCHNOTE -.-> REQUEST
"""
