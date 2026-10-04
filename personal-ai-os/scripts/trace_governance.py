"""Real, live verification CLI for this project's governance/sandbox
wiring, per the user's ask: "lets get into production ai engineering and
establish governance, guardrail ... i'm thinking of sandboxes."

Checked first, honestly: a real governance layer (PolicyEngine: classify
-> permission check -> approval -> execute -> audit) already existed, but
the live chat-agent path (ToolAgent, behind Orchestrator -- what every
real request actually goes through) called tool.call() directly,
completely bypassing it. And no tool call anywhere ran with any real
process isolation or resource limits.

This script demonstrates, live, against the real Gemini API:
  1. A READ-classified tool call (calculator) running through the real
     PolicyEngine's real sandboxed execution (app/platform/sandbox.py) --
     no approval needed, but genuinely process-isolated now.
  2. The same tool, with its classification overridden to ACT, genuinely
     stopping the request mid-flight with a real ApprovalPending --
     proving the governance gate actually reaches a real chat request,
     not just separate domain-workflow code.
  3. A deliberately slow tool genuinely timing out inside the real
     sandbox, proving the real, enforced wall-clock limit.

Usage:
    PYTHONPATH=. python scripts/trace_governance.py
"""

from app.actions.audit_log import AuditLog
from app.actions.classification import ActionClassifier
from app.actions.models import ActionClass
from app.actions.policy_engine import PolicyEngine
from app.agents.orchestrator import Orchestrator
from app.config import require_gemini_key
from app.db.connection import get_connection
from app.platform.sandbox import SandboxedToolExecutor, SandboxLimits, SandboxViolation
from app.providers.gemini_provider import GeminiProvider
from app.safety.permissions import PermissionChecker
from app.tools.calculator import CalculatorTool


def _print_header(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def demo_read_tool_through_real_policy_engine_and_sandbox() -> None:
    _print_header("1. READ tool, real PolicyEngine + real sandbox, no approval needed")
    llm = GeminiProvider()
    classifier = ActionClassifier()  # calculator defaults to READ
    policy_engine = PolicyEngine(
        classifier, PermissionChecker({"compute:local"}),
        AuditLog(get_connection(":memory:")), {"calculator": CalculatorTool()},
    )
    orchestrator = Orchestrator(llm, policy_engine=policy_engine)
    result = orchestrator.handle("What is 47 times 12?")
    print(f"Output: {result.output}")
    print(f"Tool calls: {result.tool_calls}")
    print(f"Stop reason: {result.stop_reason}")
    assert result.stop_reason == "task_completed"
    assert result.tool_calls == ["calculator"]


def demo_act_tool_genuinely_blocks_on_real_approval() -> None:
    _print_header("2. ACT-classified tool, real request genuinely stops for human approval")
    llm = GeminiProvider()
    classifier = ActionClassifier(overrides={"calculator": ActionClass.ACT})
    policy_engine = PolicyEngine(
        classifier, PermissionChecker({"compute:local"}),
        AuditLog(get_connection(":memory:")), {"calculator": CalculatorTool()},
    )
    orchestrator = Orchestrator(llm, policy_engine=policy_engine)
    result = orchestrator.handle("What is 47 times 12?")
    print(f"Output: {result.output}")
    print(f"Stop reason: {result.stop_reason}")
    print(f"Pending action id: {result.pending_action_id}")
    assert result.stop_reason == "approval_pending"
    assert result.pending_action_id is not None

    print("\nApproving the pending action via the real PolicyEngine API...")
    execution_result = policy_engine.resume_after_approval(
        result.pending_action_id, approved=True, approved_by="demo_user"
    )
    print(f"Real execution result after approval: {execution_result}")


def demo_real_sandbox_timeout() -> None:
    _print_header("3. A real tool that hangs -- genuinely killed by the real sandbox timeout")
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tests.fakes.slow_tool import SlowTool
    from app.actions.models import RiskLevel

    executor = SandboxedToolExecutor({RiskLevel.HIGH: SandboxLimits(timeout_seconds=2.0, memory_limit_mb=256)})
    try:
        executor.execute(SlowTool(), {"seconds": 10.0}, risk_level=RiskLevel.HIGH)
        print("UNEXPECTED: did not time out")
    except SandboxViolation as exc:
        print(f"Real SandboxViolation (timeout), as expected: {exc}")


def main() -> None:
    require_gemini_key()
    demo_read_tool_through_real_policy_engine_and_sandbox()
    demo_act_tool_genuinely_blocks_on_real_approval()
    demo_real_sandbox_timeout()
    _print_header("All governance/sandbox demos completed")


if __name__ == "__main__":
    main()
