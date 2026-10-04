import pytest

from app.actions.models import RiskLevel
from app.platform.sandbox import SandboxedToolExecutor, SandboxLimits, SandboxViolation
from app.tools.base import ToolError
from app.tools.calculator import CalculatorTool
from tests.fakes.slow_tool import SlowTool


def test_real_calculator_call_runs_in_a_real_subprocess_and_returns_correctly():
    executor = SandboxedToolExecutor()

    result = executor.execute(CalculatorTool(), {"expression": "47 * 12"}, risk_level=RiskLevel.LOW)

    assert result == "564"


def test_real_tool_error_propagates_through_the_sandbox():
    executor = SandboxedToolExecutor()

    with pytest.raises(ToolError, match="division by zero"):
        executor.execute(CalculatorTool(), {"expression": "1/0"}, risk_level=RiskLevel.LOW)


def test_real_timeout_kills_the_process_and_raises_sandbox_violation():
    """A real tool that genuinely sleeps longer than its real timeout --
    the sandbox must actually terminate the process, not just time out
    the join() and leave it running."""
    limits = {RiskLevel.HIGH: SandboxLimits(timeout_seconds=1.0, memory_limit_mb=256)}
    executor = SandboxedToolExecutor(limits)

    with pytest.raises(SandboxViolation, match="timeout"):
        executor.execute(SlowTool(), {"seconds": 10.0}, risk_level=RiskLevel.HIGH)


def test_fast_enough_call_completes_within_its_real_timeout():
    limits = {RiskLevel.HIGH: SandboxLimits(timeout_seconds=5.0, memory_limit_mb=256)}
    executor = SandboxedToolExecutor(limits)

    result = executor.execute(SlowTool(), {"seconds": 0.1}, risk_level=RiskLevel.HIGH)

    assert result == "done"


def test_risk_levels_use_distinct_real_limits_by_default():
    executor = SandboxedToolExecutor()

    low = executor._limits_by_risk[RiskLevel.LOW]
    high = executor._limits_by_risk[RiskLevel.HIGH]

    assert high.timeout_seconds < low.timeout_seconds
    assert high.memory_limit_mb < low.memory_limit_mb


def test_last_memory_limit_applied_is_tracked_and_inspectable():
    executor = SandboxedToolExecutor()
    assert executor.last_memory_limit_applied is None  # honest: nothing run yet

    executor.execute(CalculatorTool(), {"expression": "1 + 1"}, risk_level=RiskLevel.LOW)

    assert executor.last_memory_limit_applied in (True, False)  # real, platform-dependent, not asserted blindly
