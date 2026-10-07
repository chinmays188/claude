"""Retries the real, live multi-agent end-to-end completion that was
previously blocked by a genuine, sustained Gemini-side capacity
constraint (503 UNAVAILABLE, "high demand") -- see specs/orchestration.md's
"Live verification status" section for the full original attempt.
MultiAgentPlanner's planning decision WAS verified live and correct at
that time; MultiAgentCoordinator's actual sequential execution to a
final combined output was not, only via scripted tests. This script
retries the exact same real request now that time has passed.

Usage:
    PYTHONPATH=. python scripts/generate_multi_agent_completion_example.py
"""

import json
from pathlib import Path

from app.agents.orchestrator import ClarificationNeeded, Orchestrator
from app.config import require_gemini_key
from app.providers.gemini_provider import GeminiProvider

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "multi_agent_completion_example.json"

# The exact real request from specs/orchestration.md's original attempt --
# genuinely needs all 3 agents, SEQUENTIAL (each feeds the next).
REQUEST = (
    "Research the pros/cons of Kubernetes, compare it against ECS for our "
    "use case, and give me a 30-day adoption plan."
)


def main() -> None:
    require_gemini_key()
    llm = GeminiProvider()

    plans_observed = []
    orchestrator = Orchestrator(llm, on_multi_agent_planned=lambda p: plans_observed.append(p))

    print(f"Request: {REQUEST}")
    result = orchestrator.handle(REQUEST)

    if isinstance(result, ClarificationNeeded):
        out = {"outcome": "clarification_needed", "message": result.message, "request": REQUEST}
        print(f"ClarificationNeeded: {result.message}")
    else:
        plan = plans_observed[0] if plans_observed else None
        out = {
            "outcome": "completed",
            "request": REQUEST,
            "plan_mode": plan.mode.value if plan else None,
            "plan_agents": [a.value for a in plan.agents] if plan else None,
            "plan_reasoning": plan.reasoning if plan else None,
            "agent": result.agent,
            "output": result.output,
            "tool_calls": result.tool_calls,
            "stop_reason": result.stop_reason,
        }
        print(f"Plan: {out['plan_mode']} across {out['plan_agents']}")
        print(f"Stop reason: {result.stop_reason}")
        print(f"\n--- Final combined output ---\n{result.output}")

    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nWrote real multi-agent completion example to {OUT_PATH}")


if __name__ == "__main__":
    main()
