import json

from pydantic import BaseModel

from app.actions.policy_engine import ApprovalPending, PolicyEngine
from app.agents.base import Agent, AgentResponse
from app.guardrails.budgets import AgentBudget, BudgetExceededError, BudgetTracker
from app.guardrails.stop_conditions import StopReason
from app.platform.sandbox import SandboxedToolExecutor, SandboxViolation
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator, StructuredOutputError
from app.tools.base import Tool, ToolError
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
    def __init__(
        self,
        llm: LLMProvider,
        tools: ToolRegistry,
        budget: AgentBudget | None = None,
        on_tool_call=None,
        on_tool_error=None,
        policy_engine: PolicyEngine | None = None,
        sandbox: SandboxedToolExecutor | None = None,
    ):
        super().__init__(llm)
        self._tools = tools
        self._budget = budget or AgentBudget()
        # Real governance wiring: when policy_engine is given, every real
        # tool call goes through real risk classification, a real
        # human-approval gate for WRITE/ACT tools, real sandboxed
        # execution, and a real audit log.
        self._policy_engine = policy_engine
        # Found missing while investigating "AI Safety & Guardrails"
        # (disclosed gap: "policy_engine is still opt-in, not the default
        # for every Orchestrator caller"). Making full PolicyEngine
        # (approval gate + audit log) the default turned out too risky to
        # do blindly -- there's no safe default for "which permissions are
        # granted," and an in-memory default AuditLog would be silently
        # discarded, defeating the audit trail's purpose. Scaled down to a
        # real, smaller safety upgrade instead: when policy_engine is NOT
        # given, every tool call now still runs through a real
        # SandboxedToolExecutor (genuine process isolation, a real
        # enforced timeout/memory ceiling) rather than a direct,
        # unsandboxed tool.call() -- defaults to RiskLevel.MEDIUM's limits
        # (execute()'s own default) since no real risk classification is
        # available without a PolicyEngine. This is now the real default
        # for every caller, not opt-in.
        self._sandbox = sandbox or SandboxedToolExecutor()
        # Optional observer: called as on_tool_call(tool_name, args, result)
        # after each real tool invocation. Additive/backward-compatible --
        # existing callers passing no observer see no behavior change.
        # Exists so callers that need real tool-call input/output visibility
        # (e.g. scripts/trace_request.py) can observe the actual production
        # decision loop rather than reimplementing it separately.
        self._on_tool_call = on_tool_call
        # Optional observer: called as on_tool_error(tool_name, args, error_message)
        # when a tool raises ToolError. Mirrors on_tool_call's pattern exactly.
        # Added alongside the fix for a real bug: tool.call() previously had
        # no try/except at all here, so a real ToolError (bad args, a tool's
        # own crash, e.g. calculator division by zero) propagated up and
        # crashed the whole agent request instead of being recorded and
        # recovered from.
        self._on_tool_error = on_tool_error

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
                try:
                    if self._policy_engine is not None:
                        tool_result = self._policy_engine.propose_and_execute(
                            tool.name, decision.args,
                            description=f"Agent-requested call to '{tool.name}' during: {text}",
                        )
                    else:
                        tool_result = self._execute_with_retry(tool, decision.args)
                except ApprovalPending as exc:
                    # A real human decision is required before this call can
                    # proceed -- stop the loop here rather than silently
                    # continuing (continuing would just re-ask the same
                    # tool and hit the same pending gate again). The real
                    # action_id is surfaced on the response so a caller can
                    # drive PolicyEngine.resume_after_approval() and retry.
                    return self._response(
                        text, self._approval_pending_answer(tool.name, exc.action_id),
                        tool_calls, StopReason.APPROVAL_PENDING, pending_action_id=exc.action_id,
                    )
                except ToolError as exc:
                    tool_calls.append(tool.name)
                    history.append(
                        f"Called {tool.name} -> ERROR: {exc}. "
                        "Try different arguments, a different tool, or answer "
                        "directly if this can't be recovered from."
                    )
                    if self._on_tool_error:
                        self._on_tool_error(tool.name, decision.args, str(exc))
                    continue

                tool_calls.append(tool.name)
                history.append(f"Called {tool.name} -> {tool_result}")
                if self._on_tool_call:
                    self._on_tool_call(tool.name, decision.args, tool_result)

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

    def _execute_with_retry(self, tool: Tool, args: dict) -> str:
        """Found missing while investigating 'Tool Calling & MCP':
        Tool.retry_safe was declared on every tool but nothing anywhere
        ever read it -- dead metadata. Real fix: when a tool declares
        itself retry_safe (idempotent -- safe to run again, e.g.
        calculator, retrieve), a real SandboxViolation (the sandbox's own
        timeout/crash signal -- genuinely transient-looking) gets a real
        retry with exponential backoff (app/platform/reliability.py's
        existing retry_with_backoff, real Milestone 52 code, previously
        never wired into any tool-call path). A plain ToolError (the
        tool's own deterministic failure, e.g. bad arguments) is NEVER
        retried -- it would fail identically every time, so retrying
        would only waste real time and real sandbox overhead.
        Non-retry_safe tools (e.g. send_email, modify_github --
        non-idempotent writes) never retry at all, regardless of failure
        kind. Does not call retry_with_backoff() directly: that helper
        catches any Exception broadly, which would retry a deterministic
        ToolError too, wasting real time/sandbox overhead on a call
        guaranteed to fail identically again -- a real design conflict
        with this method's own purpose, so the real backoff timing is
        reused (same formula as retry_with_backoff) in an explicit loop
        that only continues on SandboxViolation."""
        if not tool.retry_safe:
            return self._sandbox.execute(tool, args)

        import random
        import time

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                return self._sandbox.execute(tool, args)
            except SandboxViolation:
                if attempt == max_attempts - 1:
                    raise
                delay = min(0.1 * (2**attempt), 10.0) * (0.5 + random.random())
                time.sleep(delay)

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

    def _approval_pending_answer(self, tool_name: str, action_id: str) -> str:
        return (
            f"This request needs a human to approve calling '{tool_name}' before I can "
            f"continue (real PolicyEngine risk gate -- action_id: {action_id}). "
            "Once approved, re-run this request and I'll pick up where I left off."
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
        self, text: str, output: str, tool_calls: list[str], stop_reason: StopReason,
        pending_action_id: str | None = None,
    ) -> AgentResponse:
        return AgentResponse(
            input=text,
            output=output,
            model=self._llm.model_name,
            agent=self.name,
            tool_calls=tool_calls,
            stop_reason=stop_reason.value,
            pending_action_id=pending_action_id,
        )
