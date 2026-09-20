from app.domains.pm.models import SprintPlan
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

SPRINT_PLAN_PROMPT = """Create a sprint plan from these input sources. Do not
fabricate stakeholder requests or commitments not listed below (Section 38).

Stakeholder requests:
{stakeholder_requests}

Product backlog:
{backlog}

Bug reports:
{bugs}

Commitments:
{commitments}

Respond with ONLY a JSON object matching this schema:
{{
  "prioritized_work": [{{"title": "<item>", "source": "stakeholder_request" | "backlog" | "bug" | "commitment", "priority": <0.0-1.0>, "owner": "<name or empty>", "dependencies": ["<other item title>"], "risk": "<risk description or empty>"}}],
  "risks": ["<overall sprint risk>"],
  "suggested_sprint_scope": ["<item title included in this sprint>"]
}}
"""


def create_sprint_plan(
    llm: LLMProvider,
    stakeholder_requests: list[str],
    backlog: list[str],
    bugs: list[str],
    commitments: list[str],
) -> SprintPlan:
    """Section 18: prioritizes across all 4 input sources into one plan.
    IMPORTANT: this function only produces a plan — it never writes to Jira or
    any project-management tool (Section 18: 'The system should NOT
    automatically change Jira/project management tools without approval').
    Any actual write to an external PM tool must go through Phase 2's
    PolicyEngine (app/actions/policy_engine.py) as an ACT-class action."""
    generator = RepairableGenerator(llm, SprintPlan)
    prompt = SPRINT_PLAN_PROMPT.format(
        stakeholder_requests="\n".join(f"- {r}" for r in stakeholder_requests) or "(none)",
        backlog="\n".join(f"- {b}" for b in backlog) or "(none)",
        bugs="\n".join(f"- {b}" for b in bugs) or "(none)",
        commitments="\n".join(f"- {c}" for c in commitments) or "(none)",
    )
    return generator.generate(prompt)
