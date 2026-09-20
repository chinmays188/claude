import pytest

from app.platform.reliability import (
    CallTimeoutError,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    retry_with_backoff,
    with_timeout,
)


def test_with_timeout_passes_fast_call():
    result = with_timeout(lambda: 42, timeout_seconds=10)

    assert result == 42


def test_with_timeout_raises_for_slow_call():
    import time

    def slow():
        time.sleep(0.05)
        return "done"

    with pytest.raises(CallTimeoutError):
        with_timeout(slow, timeout_seconds=0.01)


def test_retry_with_backoff_succeeds_after_transient_failures():
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("transient")
        return "success"

    result = retry_with_backoff(flaky, max_attempts=5, base_delay_seconds=0.001, jitter=False, sleep_fn=lambda s: None)

    assert result == "success"
    assert attempts["count"] == 3


def test_retry_with_backoff_raises_last_exception_after_exhausting_attempts():
    def always_fails():
        raise ValueError("permanent failure")

    with pytest.raises(ValueError, match="permanent failure"):
        retry_with_backoff(always_fails, max_attempts=3, base_delay_seconds=0.001, sleep_fn=lambda s: None)


def test_retry_with_backoff_rejects_non_positive_max_attempts():
    with pytest.raises(ValueError):
        retry_with_backoff(lambda: None, max_attempts=0)


def test_retry_with_backoff_delays_grow_exponentially():
    delays = []

    def always_fails():
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        retry_with_backoff(always_fails, max_attempts=4, base_delay_seconds=1.0, jitter=False, sleep_fn=lambda s: delays.append(s))

    assert delays == [1.0, 2.0, 4.0]


def test_circuit_breaker_starts_closed():
    breaker = CircuitBreaker()

    assert breaker.state == CircuitState.CLOSED


def test_circuit_breaker_opens_after_threshold_failures():
    breaker = CircuitBreaker(failure_threshold=3)

    for _ in range(3):
        try:
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("down")))
        except RuntimeError:
            pass

    assert breaker.state == CircuitState.OPEN


def test_circuit_breaker_rejects_calls_when_open():
    breaker = CircuitBreaker(failure_threshold=1)
    try:
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("down")))
    except RuntimeError:
        pass

    with pytest.raises(CircuitBreakerOpenError):
        breaker.call(lambda: "should not run")


def test_circuit_breaker_half_opens_after_reset_timeout():
    breaker = CircuitBreaker(failure_threshold=1, reset_timeout_seconds=0.01)
    try:
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("down")))
    except RuntimeError:
        pass

    import time
    time.sleep(0.02)

    assert breaker.state == CircuitState.HALF_OPEN


def test_circuit_breaker_closes_again_after_successful_call():
    breaker = CircuitBreaker(failure_threshold=1, reset_timeout_seconds=0.01)
    try:
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("down")))
    except RuntimeError:
        pass

    import time
    time.sleep(0.02)

    result = breaker.call(lambda: "recovered")

    assert result == "recovered"
    assert breaker.state == CircuitState.CLOSED
