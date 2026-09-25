from app.agents.planner_agent import PlannerAgent
from app.guardrails.stop_conditions import StopReason
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_answers_directly_when_no_tool_needed():
    """Regression guard for the historical behavior: PlannerAgent was
    previously a plain single-shot Agent. It must still be able to answer
    directly without a tool call -- becoming a ToolAgent must not force
    every request through a tool."""
    llm = ScriptedProvider(['{"action": "final_answer", "answer": "Week 1: Docker basics..."}'])
    agent = PlannerAgent(llm)

    result = agent.run("Create a 30-day plan for learning Docker.")

    assert result.tool_calls == []
    assert result.agent == "planner_agent"
    assert result.stop_reason == StopReason.TASK_COMPLETED.value


def test_can_call_calculator_when_plan_needs_real_arithmetic():
    """PlannerAgent previously had no ability to call any tool at all, even
    when a plan genuinely required a real calculation (e.g. a savings
    timeline)."""
    llm = ScriptedProvider(
        [
            '{"action": "call_tool", "tool": "calculator", "args": {"expression": "500 * 6"}}',
            '{"action": "final_answer", "answer": "Saving 500/month for 6 months gets you to 3000."}',
        ]
    )
    agent = PlannerAgent(llm)

    result = agent.run("Plan how many months to save 3000 at 500/month.")

    assert result.tool_calls == ["calculator"]
    assert "3000" in result.output
