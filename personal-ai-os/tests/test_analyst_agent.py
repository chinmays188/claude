from app.agents.analyst_agent import AnalystAgent
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
    """Regression guard for the historical behavior: AnalystAgent was
    previously a plain single-shot Agent. It must still be able to answer
    directly without a tool call -- becoming a ToolAgent must not force
    every request through a tool."""
    llm = ScriptedProvider(
        ['{"action": "final_answer", "answer": "RAG is better for freshness; fine-tuning for style."}']
    )
    agent = AnalystAgent(llm)

    result = agent.run("Compare RAG and fine-tuning.")

    assert result.tool_calls == []
    assert result.agent == "analyst_agent"
    assert result.stop_reason == StopReason.TASK_COMPLETED.value


def test_can_call_calculator_when_analysis_needs_real_arithmetic():
    """The whole point of this change: AnalystAgent previously had no
    ability to call any tool at all, even when comparing options genuinely
    required a real calculation."""
    llm = ScriptedProvider(
        [
            '{"action": "call_tool", "tool": "calculator", "args": {"expression": "1500 * 12"}}',
            '{"action": "final_answer", "answer": "Option A costs 18000/year, which is cheaper."}',
        ]
    )
    agent = AnalystAgent(llm)

    result = agent.run("Which costs more: 1500/month or a flat 20000/year?")

    assert result.tool_calls == ["calculator"]
    assert "18000" in result.output
