import json

from pydantic import BaseModel

from app.agents.base import Agent, AgentResponse
from app.guardrails.budgets import AgentBudget, BudgetExceededError, BudgetTracker
from app.guardrails.stop_conditions import StopReason
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator, StructuredOutputError
from app.tools.registry import ToolRegistry, UnknownToolError

DECISION_PROMPT = """{system_prompt}

You have access to these tools:
{tool_descriptions}

Conversation so far:
{history}

User request: {text}

Decide the next step. Respond with ONLY one JSON object:
- To call a tool: {{"action": "call_tool", "tool": "<tool_name>", "args": {{...}}}}
- To give the final answer: {{"action": "final_answer", "answer": "<answer text>"}}
"""


class AgentDecision(BaseModel):
    action: str
    tool: str | None = None
    args: dict = {}
    answer: str | None = None


class ToolAgent(Agent):
    def __init__(self, llm: LLMProvider, tools: ToolRegistry, budget: AgentBudget | None = None):
        super().__init__(llm)
        self._tools = tools
        self._budget = budget or AgentBudget()

    def run(self, text: str) -> AgentResponse:
        if not text or not text.strip():
            raise ValueError("Input text must not be empty.")

        tracker = BudgetTracker(self._budget)
        history: list[str] = []
        tool_calls: list[str] = []

        while True:
            try:
                tracker.record_turn()
                decision = self._decide(text, history)

                if decision.action == "final_answer" and decision.answer:
                    return self._response(
                        text, decision.answer, tool_calls, StopReason.TASK_COMPLETED
                    )

                tool = self._resolve_tool(decision.tool)
                if tool is None:
                    history.append(
                        "System: requested tool was unavailable or invalid; "
                        "answer directly instead."
                    )
                    continue

                tracker.record_tool_call()
                tool_result = tool.call(decision.args)
                tool_calls.append(tool.name)
                history.append(f"Called {tool.name} -> {tool_result}")

            except BudgetExceededError as exc:
                return self._response(
                    text,
                    self._degraded_answer(str(exc)),
                    tool_calls,
                    self._budget_stop_reason(exc),
                )

    def _resolve_tool(self, tool_name: str | None):
        if tool_name is None:
            return None
        try:
            return self._tools.get(tool_name)
        except UnknownToolError:
            return None

    def _decide(self, text: str, history: list[str]) -> AgentDecision:
        prompt = DECISION_PROMPT.format(
            system_prompt=self.system_prompt,
            tool_descriptions=json.dumps(self._tools.descriptions()),
            history="\n".join(history) if history else "(none yet)",
            text=text,
        )
        generator = RepairableGenerator(self._llm, AgentDecision)
        try:
            return generator.generate(prompt)
        except StructuredOutputError:
            return AgentDecision(
                action="final_answer",
                answer=(
                    "I had trouble formulating a response for this request. "
                    "Could you rephrase it?"
                ),
            )

    def _degraded_answer(self, reason: str) -> str:
        return (
            "I couldn't fully complete this request within the allowed budget "
            f"({reason}). Here is what I have so far; the answer may be incomplete."
        )

    def _budget_stop_reason(self, exc: BudgetExceededError) -> StopReason:
        message = str(exc)
        if "max_turns" in message:
            return StopReason.MAX_TURNS_REACHED
        if "max_tool_calls" in message:
            return StopReason.MAX_TOOL_CALLS_REACHED
        if "timeout" in message:
            return StopReason.TIMEOUT
        return StopReason.MAX_TURNS_REACHED

    def _response(
        self, text: str, output: str, tool_calls: list[str], stop_reason: StopReason
    ) -> AgentResponse:
        return AgentResponse(
            input=text,
            output=output,
            model=self._llm.model_name,
            agent=self.name,
            tool_calls=tool_calls,
            stop_reason=stop_reason.value,
        )
