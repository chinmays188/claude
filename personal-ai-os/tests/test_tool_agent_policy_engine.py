from pydantic import BaseModel

from app.actions.audit_log import AuditLog
from app.actions.classification import ActionClassifier
from app.actions.policy_engine import PolicyEngine
from app.agents.tool_agent import ToolAgent
from app.db.connection import get_connection
from app.guardrails.stop_conditions import StopReason
from app.providers.base import LLMProvider
from app.safety.permissions import PermissionChecker
from app.tools.base import Tool
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


class SendArgs(BaseModel):
    to: str
    message: str


class FakeSendEmailTool(Tool):
    """Module-level (not test-local) so it's importable for the real
    sandbox's spawn-based multiprocessing -- mirrors
    tests/test_policy_engine.py's own FakeSendEmailTool exactly."""

    name = "send_email"
    description = "sends an email"
    args_schema = SendArgs
    permissions = ["write:email"]

    def run(self, args: SendArgs) -> str:
        return f"Sent to {args.to}: {args.message}"


def _policy_engine(granted_permissions: set[str]) -> PolicyEngine:
    classifier = ActionClassifier()
    permission_checker = PermissionChecker(granted_permissions)
    audit_log = AuditLog(get_connection(":memory:"))
    tools = {"calculator": CalculatorTool(), "send_email": FakeSendEmailTool()}
    return PolicyEngine(classifier, permission_checker, audit_log, tools)


def test_without_policy_engine_tool_calls_run_exactly_as_before():
    """Backward compatibility: every existing caller (no policy_engine
    given) sees identical behavior to before this change."""
    llm = ScriptedProvider(
        [
            '{"action": "call_tool", "tool": "calculator", "args": {"expression": "47 * 12"}}',
            '{"action": "final_answer", "answer": "564"}',
        ]
    )
    agent = ToolAgent(llm, tools=ToolRegistry([CalculatorTool()]))

    result = agent.run("What is 47 * 12?")

    assert result.tool_calls == ["calculator"]
    assert result.stop_reason == StopReason.TASK_COMPLETED.value
    assert result.pending_action_id is None


def test_read_classified_tool_executes_through_real_policy_engine_and_sandbox():
    """calculator is READ-classified -- no approval needed, but it now
    genuinely runs through PolicyEngine's real sandboxed execution, not a
    direct tool.call()."""
    llm = ScriptedProvider(
        [
            '{"action": "call_tool", "tool": "calculator", "args": {"expression": "47 * 12"}}',
            '{"action": "final_answer", "answer": "564"}',
        ]
    )
    policy_engine = _policy_engine(granted_permissions={"compute:local"})
    agent = ToolAgent(llm, tools=ToolRegistry([CalculatorTool()]), policy_engine=policy_engine)

    result = agent.run("What is 47 * 12?")

    assert result.tool_calls == ["calculator"]
    assert result.stop_reason == StopReason.TASK_COMPLETED.value
    assert result.output == "564"


def test_act_classified_tool_stops_the_loop_with_real_approval_pending():
    """send_email is WRITE/ACT-classified -- requires real human approval.
    A real governance gate now applies to the live chat-agent path, not
    just separate domain-workflow code."""
    llm = ScriptedProvider(
        [
            '{"action": "call_tool", "tool": "send_email", "args": {"to": "a@b.com", "message": "hi"}}',
        ]
    )
    policy_engine = _policy_engine(granted_permissions={"write:email"})
    agent = ToolAgent(llm, tools=ToolRegistry([FakeSendEmailTool()]), policy_engine=policy_engine)

    result = agent.run("Email a@b.com saying hi.")

    assert result.stop_reason == StopReason.APPROVAL_PENDING.value
    assert result.pending_action_id is not None
    assert "approve" in result.output.lower()
    assert result.tool_calls == []  # never actually executed -- still pending


def test_approving_the_pending_action_lets_it_actually_execute():
    """The full real loop: ToolAgent surfaces a real pending action id,
    then PolicyEngine.resume_after_approval() (the same real API domain
    workflows already use) actually runs the real sandboxed tool call."""
    llm = ScriptedProvider(
        [
            '{"action": "call_tool", "tool": "send_email", "args": {"to": "a@b.com", "message": "hi"}}',
        ]
    )
    policy_engine = _policy_engine(granted_permissions={"write:email"})
    agent = ToolAgent(llm, tools=ToolRegistry([FakeSendEmailTool()]), policy_engine=policy_engine)

    result = agent.run("Email a@b.com saying hi.")
    action_id = result.pending_action_id

    execution_result = policy_engine.resume_after_approval(action_id, approved=True, approved_by="demo_user")

    assert execution_result == "Sent to a@b.com: hi"
