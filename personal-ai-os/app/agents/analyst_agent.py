from app.agents.base import Agent


class AnalystAgent(Agent):
    name = "analyst_agent"
    system_prompt = (
        "You are an analyst agent. Compare the given options across relevant "
        "dimensions (e.g. cost, quality, complexity) and state a clear "
        "recommendation with tradeoffs."
    )
