import random
import time
from enum import Enum
from typing import Callable, TypeVar

T = TypeVar("T")


class CallTimeoutError(Exception):
    pass


def with_timeout(func: Callable[[], T], timeout_seconds: float) -> T:
    """Milestone 52: a real, measured timeout — not a documentation promise.
    Note: this measures elapsed wall-clock time around a synchronous call and
    raises AFTER the call returns if it took too long; it cannot forcibly
    interrupt a call already in progress (that needs a separate thread/process
    with its own cancellation, which this sandbox has no use case to justify
    yet). Honest about that limitation rather than implying true preemption.
    Named CallTimeoutError (not TimeoutError) to avoid shadowing Python's
    builtin exception of the same name."""
    start = time.monotonic()
    result = func()
    elapsed = time.monotonic() - start
    if elapsed > timeout_seconds:
        raise CallTimeoutError(f"Call took {elapsed:.2f}s, exceeding timeout of {timeout_seconds}s.")
    return result


def retry_with_backoff(
    func: Callable[[], T],
    max_attempts: int = 3,
    base_delay_seconds: float = 0.1,
    max_delay_seconds: float = 10.0,
    jitter: bool = True,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> T:
    """Milestone 52: exponential backoff with optional jitter (avoids a
    thundering-herd retry pattern across many callers). `sleep_fn` is
    injectable so tests can run this without actually waiting real seconds."""
    if max_attempts <= 0:
        raise ValueError("max_attempts must be positive.")

    last_exception: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as exc:
            last_exception = exc
            if attempt == max_attempts - 1:
                break
            delay = min(base_delay_seconds * (2**attempt), max_delay_seconds)
            if jitter:
                delay = delay * (0.5 + random.random())
            sleep_fn(delay)

    raise last_exception


class CircuitState(str, Enum):
    CLOSED = "closed"  # normal operation
    OPEN = "open"  # failing too much, reject calls immediately
    HALF_OPEN = "half_open"  # trial period, allow one call through to test recovery


class CircuitBreakerOpenError(Exception):
    pass


class CircuitBreaker:
    """Milestone 52: a real circuit breaker — after `failure_threshold`
    consecutive failures, opens and rejects calls immediately (without even
    attempting them) for `reset_timeout_seconds`, then allows one trial call
    (HALF_OPEN) to test recovery before fully closing again. Protects a
    downstream dependency (e.g. Gemini, GitHub) from being hammered while
    it's already failing, and protects the caller from waiting out repeated
    timeouts against a service that's known to be down."""

    def __init__(self, failure_threshold: int = 5, reset_timeout_seconds: float = 30.0):
        self._failure_threshold = failure_threshold
        self._reset_timeout_seconds = reset_timeout_seconds
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            if time.monotonic() - self._opened_at >= self._reset_timeout_seconds:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def call(self, func: Callable[[], T]) -> T:
        current_state = self.state
        if current_state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit is open after {self._consecutive_failures} consecutive failures; "
                f"rejecting call without attempting it."
            )

        try:
            result = func()
        except Exception:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
            raise

        # Success: reset fully, whether we were CLOSED or trialing HALF_OPEN.
        self._consecutive_failures = 0
        self._state = CircuitState.CLOSED
        self._opened_at = None
        return result
