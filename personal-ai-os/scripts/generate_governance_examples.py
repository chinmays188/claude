"""Generates REAL governance/sandbox examples for the dashboard, run live
once and committed as app/dashboard_ui/governance_examples.json -- same
pattern as every other *_examples.json in this project (the dashboard
never makes a live LLM call itself).

Captures the exact 3 real demos scripts/trace_governance.py already
proved live (see that script's own docstring for the full story):
  1. A READ-classified tool call running through the real PolicyEngine's
     real sandboxed execution -- no approval needed, genuinely
     process-isolated.
  2. The same tool, ACT-classified, genuinely stopping a real chat
     request mid-flight with a real ApprovalPending, then genuinely
     executing after a real PolicyEngine.resume_after_approval() call.
  3. A deliberately slow tool genuinely timing out inside the real
     sandbox -- a real SandboxViolation, not simulated.

Usage:
    PYTHONPATH=. python scripts/generate_governance_examples.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.actions.audit_log import AuditLog
from app.actions.classification import ActionClassifier
from app.actions.models import ActionClass, RiskLevel
from app.actions.policy_engine import PolicyEngine
from app.agents.orchestrator import Orchestrator
from app.config import require_gemini_key
from app.db.connection import get_connection
from app.platform.sandbox import SandboxedToolExecutor, SandboxLimits, SandboxViolation
from app.providers.gemini_provider import GeminiProvider
from app.safety.permissions import PermissionChecker
from app.tools.calculator import CalculatorTool
from tests.fakes.slow_tool import SlowTool

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "governance_examples.json"


def demo_read_path() -> dict:
    llm = GeminiProvider()
    policy_engine = PolicyEngine(
        ActionClassifier(), PermissionChecker({"compute:local"}),
        AuditLog(get_connection(":memory:")), {"calculator": CalculatorTool()},
    )
    orchestrator = Orchestrator(llm, policy_engine=policy_engine)
    result = orchestrator.handle("What is 47 times 12?")
    return {
        "scenario": "READ-classified tool, real sandbox, no approval needed",
        "request": "What is 47 times 12?",
        "output": result.output,
        "tool_calls": result.tool_calls,
        "stop_reason": result.stop_reason,
    }


def demo_act_path() -> dict:
    llm = GeminiProvider()
    classifier = ActionClassifier(overrides={"calculator": ActionClass.ACT})
    policy_engine = PolicyEngine(
        classifier, PermissionChecker({"compute:local"}),
        AuditLog(get_connection(":memory:")), {"calculator": CalculatorTool()},
    )
    orchestrator = Orchestrator(llm, policy_engine=policy_engine)
    result = orchestrator.handle("What is 47 times 12?")
    pending_output = result.output
    pending_action_id = result.pending_action_id

    execution_result = None
    if pending_action_id:
        execution_result = policy_engine.resume_after_approval(
            pending_action_id, approved=True, approved_by="demo_user"
        )

    return {
        "scenario": "ACT-classified tool, real request stops for human approval, then executes after approval",
        "request": "What is 47 times 12?",
        "pending_output": pending_output,
        "stop_reason": result.stop_reason,
        "pending_action_id": pending_action_id,
        "execution_result_after_approval": execution_result,
    }


def demo_sandbox_timeout() -> dict:
    executor = SandboxedToolExecutor({RiskLevel.HIGH: SandboxLimits(timeout_seconds=2.0, memory_limit_mb=256)})
    try:
        executor.execute(SlowTool(), {"seconds": 10.0}, risk_level=RiskLevel.HIGH)
        return {"scenario": "sandbox timeout", "violated": False, "error": None}
    except SandboxViolation as exc:
        return {
            "scenario": "A real slow tool, genuinely killed by the real sandbox timeout",
            "violated": True,
            "error": str(exc),
            "timeout_seconds": 2.0,
        }


def main() -> None:
    require_gemini_key()
    examples = {
        "read_path": demo_read_path(),
        "act_path": demo_act_path(),
        "sandbox_timeout": demo_sandbox_timeout(),
    }
    for key, value in examples.items():
        print(f"[{key}] {json.dumps(value, indent=2)[:300]}")

    OUT_PATH.write_text(json.dumps(examples, indent=2))
    print(f"\nWrote real governance examples to {OUT_PATH}")


if __name__ == "__main__":
    main()
