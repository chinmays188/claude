import time
from dataclasses import dataclass


@dataclass
class AgentBudget:
    max_turns: int = 8
    max_tool_calls: int = 6
    max_tokens: int | None = None
    max_retries: int = 2
    timeout_seconds: float = 30.0


class BudgetExceededError(Exception):
    """Raised when a budget limit is hit — signals the agent must stop, not retry silently."""


class BudgetTracker:
    """Tracks consumption against an AgentBudget for a single agent run."""

    def __init__(self, budget: AgentBudget):
        self._budget = budget
        self.turns = 0
        self.tool_calls = 0
        self.tokens = 0
        self.retries = 0
        self._start_time = time.monotonic()

    def record_turn(self) -> None:
        self.turns += 1
        if self.turns > self._budget.max_turns:
            raise BudgetExceededError(
                f"max_turns exceeded ({self.turns} > {self._budget.max_turns})"
            )
        self._check_timeout()

    def record_tool_call(self) -> None:
        self.tool_calls += 1
        if self.tool_calls > self._budget.max_tool_calls:
            raise BudgetExceededError(
                f"max_tool_calls exceeded ({self.tool_calls} > {self._budget.max_tool_calls})"
            )
        self._check_timeout()

    def record_tokens(self, count: int) -> None:
        self.tokens += count
        if self._budget.max_tokens is not None and self.tokens > self._budget.max_tokens:
            raise BudgetExceededError(
                f"max_tokens exceeded ({self.tokens} > {self._budget.max_tokens})"
            )

    def record_retry(self) -> None:
        self.retries += 1
        if self.retries > self._budget.max_retries:
            raise BudgetExceededError(
                f"max_retries exceeded ({self.retries} > {self._budget.max_retries})"
            )

    def _check_timeout(self) -> None:
        elapsed = time.monotonic() - self._start_time
        if elapsed > self._budget.timeout_seconds:
            raise BudgetExceededError(
                f"timeout_seconds exceeded ({elapsed:.1f}s > {self._budget.timeout_seconds}s)"
            )
