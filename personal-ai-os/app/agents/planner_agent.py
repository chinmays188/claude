from app.agents.base import Agent


class PlannerAgent(Agent):
    name = "planner_agent"
    system_prompt = (
        "You are a planning agent. Break the goal down into a concrete, "
        "sequenced plan with milestones. Prefer specific, actionable steps "
        "over generic advice."
    )
