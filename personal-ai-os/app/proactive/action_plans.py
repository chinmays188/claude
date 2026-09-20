import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from app.actions.policy_engine import ApprovalPending, PolicyEngine
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

PLAN_PROMPT = """A signal was observed that may warrant action. Propose a plan
— a sequence of concrete steps using ONLY the tools listed below. Do not
propose a tool that isn't listed, and do not claim you have already taken any
action (Phase 4's rule: AI should not directly execute consequential actions
without approval).

Observed signal: {signal_description}

Available tools: {available_tools}

Respond with ONLY a JSON object:
{{"steps": [{{"tool_name": "<one of the available tools>", "args": {{...}}, "description": "<what this step does and why>"}}]}}
"""


class PlanStepStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class PlanStep(BaseModel):
    step_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    tool_name: str
    args: dict
    description: str
    status: PlanStepStatus = PlanStepStatus.PENDING
    action_id: str | None = None  # PolicyEngine's ActionProposal.action_id, once proposed
    result: str | None = None


class ActionPlan(BaseModel):
    """Milestone 36: a multi-step plan, proposed but never auto-executed.
    Phase 4's loop made explicit: OBSERVE (the signal) -> REASON (this plan's
    steps + description) -> PROPOSE (this object) -> APPROVE (per-step, via
    PolicyEngine) -> ACT -> VERIFY."""

    plan_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    owner_id: str
    triggered_by_signal_id: str | None = None
    steps: list[PlanStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class _RawStep(BaseModel):
    tool_name: str
    args: dict
    description: str


class _RawPlan(BaseModel):
    steps: list[_RawStep]


def propose_plan(
    llm: LLMProvider, owner_id: str, signal_description: str, available_tool_names: list[str],
    triggered_by_signal_id: str | None = None,
) -> ActionPlan:
    """Milestone 36's REASON+PROPOSE steps. The plan itself never executes
    anything — every step starts PENDING and must go through PolicyEngine's
    normal approval flow (execute_step below) before anything runs."""
    generator = RepairableGenerator(llm, _RawPlan)
    prompt = PLAN_PROMPT.format(signal_description=signal_description, available_tools=", ".join(available_tool_names))
    raw = generator.generate(prompt)

    steps = [
        PlanStep(tool_name=s.tool_name, args=s.args, description=s.description)
        for s in raw.steps
        if s.tool_name in available_tool_names  # drop any hallucinated tool name outright, never propose it
    ]
    return ActionPlan(owner_id=owner_id, triggered_by_signal_id=triggered_by_signal_id, steps=steps)


def execute_step(policy_engine: PolicyEngine, plan: ActionPlan, step_id: str) -> PlanStep:
    """Milestone 36/37's APPROVE->ACT->VERIFY: executes exactly one step of a
    plan through the existing PolicyEngine (Phase 2, Milestone 25) — READ
    steps execute immediately (still audited); WRITE/ACT steps raise
    ApprovalPending exactly as any other PolicyEngine action would."""
    step = next((s for s in plan.steps if s.step_id == step_id), None)
    if step is None:
        raise ValueError(f"No step with id '{step_id}' in plan '{plan.plan_id}'.")

    try:
        result = policy_engine.propose_and_execute(step.tool_name, step.args, step.description)
    except ApprovalPending as exc:
        step.action_id = exc.action_id
        step.status = PlanStepStatus.PENDING
        raise

    step.status = PlanStepStatus.EXECUTED
    step.result = result
    return step


def resume_step(policy_engine: PolicyEngine, plan: ActionPlan, step_id: str, approved: bool, approved_by: str) -> PlanStep:
    step = next((s for s in plan.steps if s.step_id == step_id), None)
    if step is None:
        raise ValueError(f"No step with id '{step_id}' in plan '{plan.plan_id}'.")
    if step.action_id is None:
        raise ValueError(f"Step '{step_id}' was never proposed via execute_step() — nothing pending to resume.")

    result = policy_engine.resume_after_approval(step.action_id, approved=approved, approved_by=approved_by)
    step.status = PlanStepStatus.EXECUTED if approved else PlanStepStatus.REJECTED
    step.result = result
    return step
