# Orchestrator / Multi-Agent Routing

## Example 1 — Research

Input:
"Explain RAG."

Expected:
- Classifier returns `task_type=research`
- `ResearchAgent` handles the request
- `AgentResponse.agent == "research_agent"`

## Example 2 — Analysis

Input:
"Compare RAG, fine-tuning and long-context prompting."

Expected:
- Classifier returns `task_type=analysis`
- `AnalystAgent` handles the request
- `AgentResponse.agent == "analyst_agent"`

## Example 3 — Planning

Input:
"Create a 30-day plan for learning Docker."

Expected:
- Classifier returns `task_type=planning`
- `PlannerAgent` handles the request
- `AgentResponse.agent == "planner_agent"`

## Example 4 — Ambiguous input

Input:
"Do something useful."

Expected:
- Classifier returns `task_type=unclear` (or confidence below threshold)
- Orchestrator does NOT guess an agent
- Returns a `ClarificationNeeded` response asking the user what they meant
- No agent is invoked, no LLM call beyond classification

## Edge case — Empty input

Input:
""

Expected:
- Orchestrator raises a validation error before calling the classifier

## Failure case — Malformed classifier output

Condition:
Classifier LLM call returns text that isn't valid JSON, or JSON missing required fields.

Expected:
- `ClassificationError` raised
- Orchestrator does not silently default to an agent
- (Repair loop for this is deferred to Milestone 4 — Structured Output)

## Failure case — Low-confidence classification

Condition:
Classifier returns a valid `task_type` but `confidence` below the configured threshold (default 0.5).

Expected:
- Treated as `unclear` regardless of the raw `task_type`
- Orchestrator returns `ClarificationNeeded`
