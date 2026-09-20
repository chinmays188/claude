import pytest

from app.agents.tool_agent import ToolAgent
from app.guardrails.budgets import AgentBudget
from app.guardrails.stop_conditions import StopReason
from app.providers.base import LLMProvider
from app.tools.base import ArgumentValidationError
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


class LoopingProvider(LLMProvider):
    """Always returns the same tool-call decision, simulating a runaway agent."""

    def __init__(self, response: str):
        self._response = response

    def generate(self, prompt: str) -> str:
        return self._response

    @property
    def model_name(self) -> str:
        return "looping-model"


def _agent(responses: list[str], budget: AgentBudget | None = None) -> ToolAgent:
    llm = ScriptedProvider(responses)
    return ToolAgent(llm, tools=ToolRegistry([CalculatorTool()]), budget=budget)


def test_calls_calculator_when_needed():
    agent = _agent(
        [
            '{"action": "call_tool", "tool": "calculator", "args": {"expression": "47 * 12"}}',
            '{"action": "final_answer", "answer": "47 times 12 is 564."}',
        ]
    )

    result = agent.run("What is 47 * 12?")

    assert result.tool_calls == ["calculator"]
    assert "564" in result.output
    assert result.stop_reason == StopReason.TASK_COMPLETED.value


def test_on_tool_call_observer_receives_real_args_and_result():
    """The optional on_tool_call hook (added for scripts/trace_request.py's
    tool-call I/O visibility) must fire with the actual args and result of
    each real tool invocation, and must not fire when no tool is called."""
    observed = []
    llm = ScriptedProvider(
        [
            '{"action": "call_tool", "tool": "calculator", "args": {"expression": "47 * 12"}}',
            '{"action": "final_answer", "answer": "47 times 12 is 564."}',
        ]
    )
    agent = ToolAgent(
        llm, tools=ToolRegistry([CalculatorTool()]),
        on_tool_call=lambda name, args, result: observed.append((name, args, result)),
    )

    agent.run("What is 47 * 12?")

    assert len(observed) == 1
    name, args, result = observed[0]
    assert name == "calculator"
    assert args == {"expression": "47 * 12"}
    assert result == "564"


def test_on_tool_call_observer_not_called_when_no_tool_used():
    observed = []
    agent = ToolAgent(
        ScriptedProvider(['{"action": "final_answer", "answer": "No tool needed."}']),
        tools=ToolRegistry([CalculatorTool()]),
        on_tool_call=lambda name, args, result: observed.append((name, args, result)),
    )

    agent.run("Just say hi.")

    assert observed == []


def test_skips_tool_when_not_needed():
    agent = _agent(['{"action": "final_answer", "answer": "RAG combines retrieval with generation."}'])

    result = agent.run("Explain RAG.")

    assert result.tool_calls == []
    assert result.stop_reason == StopReason.TASK_COMPLETED.value


def test_hallucinated_tool_does_not_execute_and_agent_recovers():
    agent = _agent(
        [
            '{"action": "call_tool", "tool": "send_email", "args": {}}',
            '{"action": "final_answer", "answer": "I can\'t send emails, but here is an explanation instead."}',
        ]
    )

    result = agent.run("Send an email summarizing RAG.")

    assert result.tool_calls == []
    assert result.stop_reason == StopReason.TASK_COMPLETED.value


def test_invalid_tool_args_raise():
    agent = _agent(['{"action": "call_tool", "tool": "calculator", "args": {"expression": null}}'])

    with pytest.raises(ArgumentValidationError):
        agent.run("What is null plus one?")


def test_malformed_decision_json_repairs_then_succeeds():
    agent = _agent(
        [
            "not valid json at all",
            '{"action": "final_answer", "answer": "RAG combines retrieval with generation."}',
        ]
    )

    result = agent.run("Explain RAG.")

    assert result.tool_calls == []
    assert result.output == "RAG combines retrieval with generation."


def test_malformed_decision_json_exhausts_repairs_gracefully():
    agent = _agent(["not valid json"] * 10)

    result = agent.run("Explain RAG.")

    assert result.tool_calls == []
    assert "rephrase" in result.output.lower()


def test_decision_json_with_literal_newlines_in_answer_is_recovered():
    raw = (
        '```json\n{"action": "final_answer", "answer": "### What is RAG?\n\n'
        'RAG stands for retrieval augmented generation."}\n```'
    )
    agent = _agent([raw])

    result = agent.run("Explain RAG.")

    assert result.output == "### What is RAG?\n\nRAG stands for retrieval augmented generation."


def test_empty_input_raises():
    agent = _agent([])

    with pytest.raises(ValueError):
        agent.run("")


def test_runaway_loop_stopped_by_max_turns_budget():
    llm = LoopingProvider('{"action": "call_tool", "tool": "calculator", "args": {"expression": "1+1"}}')
    budget = AgentBudget(max_turns=3, max_tool_calls=100, timeout_seconds=30)
    agent = ToolAgent(llm, tools=ToolRegistry([CalculatorTool()]), budget=budget)

    result = agent.run("Keep calculating forever.")

    assert result.stop_reason == StopReason.MAX_TURNS_REACHED.value
    assert len(result.tool_calls) <= 3


def test_runaway_loop_stopped_by_max_tool_calls_budget():
    llm = LoopingProvider('{"action": "call_tool", "tool": "calculator", "args": {"expression": "1+1"}}')
    budget = AgentBudget(max_turns=100, max_tool_calls=2, timeout_seconds=30)
    agent = ToolAgent(llm, tools=ToolRegistry([CalculatorTool()]), budget=budget)

    result = agent.run("Keep calculating forever.")

    assert result.stop_reason == StopReason.MAX_TOOL_CALLS_REACHED.value
    assert len(result.tool_calls) == 2


def test_degraded_response_communicates_incompleteness():
    llm = LoopingProvider('{"action": "call_tool", "tool": "calculator", "args": {"expression": "1+1"}}')
    budget = AgentBudget(max_turns=1, max_tool_calls=100, timeout_seconds=30)
    agent = ToolAgent(llm, tools=ToolRegistry([CalculatorTool()]), budget=budget)

    result = agent.run("Keep calculating forever.")

    assert "budget" in result.output.lower() or "couldn't" in result.output.lower()
