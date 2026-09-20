import pytest
from pydantic import BaseModel

from app.actions.audit_log import AuditLog
from app.actions.classification import ActionClassifier
from app.actions.policy_engine import ApprovalPending, PolicyEngine
from app.db.connection import get_connection
from app.proactive.action_plans import execute_step, propose_plan, resume_step
from app.providers.base import LLMProvider
from app.safety.permissions import PermissionChecker
from app.tools.base import Tool
from app.tools.calculator import CalculatorTool


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
    name = "send_email"
    description = "sends an email"
    args_schema = SendArgs
    permissions = ["write:email"]

    def run(self, args: SendArgs) -> str:
        return f"Sent to {args.to}: {args.message}"


def _engine(granted: set[str]) -> PolicyEngine:
    classifier = ActionClassifier()
    permission_checker = PermissionChecker(granted)
    audit_log = AuditLog(get_connection(":memory:"))
    tools = {"calculator": CalculatorTool(), "send_email": FakeSendEmailTool()}
    return PolicyEngine(classifier, permission_checker, audit_log, tools)


def test_propose_plan_only_includes_available_tools():
    llm = ScriptedProvider(
        ['{"steps": [{"tool_name": "calculator", "args": {"expression": "2+2"}, "description": "compute"}, '
         '{"tool_name": "hallucinated_tool", "args": {}, "description": "should be dropped"}]}']
    )

    plan = propose_plan(llm, "alice", "A signal about needing a calculation.", available_tool_names=["calculator"])

    assert len(plan.steps) == 1
    assert plan.steps[0].tool_name == "calculator"


def test_execute_read_step_runs_immediately():
    llm = ScriptedProvider(['{"steps": [{"tool_name": "calculator", "args": {"expression": "2+2"}, "description": "compute"}]}'])
    plan = propose_plan(llm, "alice", "signal", available_tool_names=["calculator"])
    engine = _engine(granted={"compute:local"})

    step = execute_step(engine, plan, plan.steps[0].step_id)

    assert step.result == "4"
    assert step.status.value == "executed"


def test_execute_act_step_raises_approval_pending():
    llm = ScriptedProvider(
        ['{"steps": [{"tool_name": "send_email", "args": {"to": "a@b.com", "message": "hi"}, "description": "notify"}]}']
    )
    plan = propose_plan(llm, "alice", "signal", available_tool_names=["send_email"])
    engine = _engine(granted={"write:email"})

    with pytest.raises(ApprovalPending):
        execute_step(engine, plan, plan.steps[0].step_id)

    assert plan.steps[0].action_id is not None


def test_resume_step_after_approval_executes():
    llm = ScriptedProvider(
        ['{"steps": [{"tool_name": "send_email", "args": {"to": "a@b.com", "message": "hi"}, "description": "notify"}]}']
    )
    plan = propose_plan(llm, "alice", "signal", available_tool_names=["send_email"])
    engine = _engine(granted={"write:email"})

    try:
        execute_step(engine, plan, plan.steps[0].step_id)
    except ApprovalPending:
        pass

    step = resume_step(engine, plan, plan.steps[0].step_id, approved=True, approved_by="alice")

    assert "Sent to a@b.com" in step.result
    assert step.status.value == "executed"


def test_resume_step_rejection_marks_rejected():
    llm = ScriptedProvider(
        ['{"steps": [{"tool_name": "send_email", "args": {"to": "a@b.com", "message": "hi"}, "description": "notify"}]}']
    )
    plan = propose_plan(llm, "alice", "signal", available_tool_names=["send_email"])
    engine = _engine(granted={"write:email"})

    try:
        execute_step(engine, plan, plan.steps[0].step_id)
    except ApprovalPending:
        pass

    step = resume_step(engine, plan, plan.steps[0].step_id, approved=False, approved_by="alice")

    assert step.status.value == "rejected"


def test_execute_step_unknown_step_id_raises():
    llm = ScriptedProvider(['{"steps": []}'])
    plan = propose_plan(llm, "alice", "signal", available_tool_names=["calculator"])
    engine = _engine(granted=set())

    with pytest.raises(ValueError):
        execute_step(engine, plan, "does-not-exist")


def test_resume_step_without_prior_proposal_raises():
    llm = ScriptedProvider(['{"steps": [{"tool_name": "calculator", "args": {"expression": "1+1"}, "description": "d"}]}'])
    plan = propose_plan(llm, "alice", "signal", available_tool_names=["calculator"])
    engine = _engine(granted=set())

    with pytest.raises(ValueError):
        resume_step(engine, plan, plan.steps[0].step_id, approved=True, approved_by="alice")
