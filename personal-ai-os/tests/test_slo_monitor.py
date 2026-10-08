import pytest

from app.observability.traces import Trace
from app.platform.slo_monitor import SLOAlertLevel, SLOMonitor, SLOThreshold, compute_p95_latency_ms


def _trace(latency_ms: float, status: str = "success") -> Trace:
    return Trace(session_id="s", user_id="u", latency_ms=latency_ms, status=status)


def test_compute_p95_latency_empty_is_a_real_zero():
    assert compute_p95_latency_ms([]) == 0.0


def test_compute_p95_latency_over_real_traces():
    traces = [_trace(ms) for ms in [100, 200, 300, 400, 5000]]

    p95 = compute_p95_latency_ms(traces)

    assert p95 == 5000  # 95th percentile of 5 sorted values lands on the last (slowest)


def test_check_returns_ok_well_under_thresholds():
    monitor = SLOMonitor({"router": SLOThreshold(scope="router", max_p95_latency_ms=5000, max_error_rate=0.1)})
    traces = [_trace(100) for _ in range(10)]

    alert = monitor.check("router", traces)

    assert alert.level == SLOAlertLevel.OK
    assert alert.reasons == []


def test_check_returns_warning_near_latency_threshold():
    monitor = SLOMonitor(
        {"router": SLOThreshold(scope="router", max_p95_latency_ms=1000, max_error_rate=0.5, warning_fraction=0.8)}
    )
    traces = [_trace(850) for _ in range(10)]

    alert = monitor.check("router", traces)

    assert alert.level == SLOAlertLevel.WARNING
    assert "latency" in alert.reasons[0]


def test_check_returns_breached_over_latency_threshold():
    monitor = SLOMonitor({"router": SLOThreshold(scope="router", max_p95_latency_ms=1000, max_error_rate=0.5)})
    traces = [_trace(2000) for _ in range(10)]

    alert = monitor.check("router", traces)

    assert alert.level == SLOAlertLevel.BREACHED


def test_check_returns_breached_over_error_rate_threshold():
    monitor = SLOMonitor({"router": SLOThreshold(scope="router", max_p95_latency_ms=100000, max_error_rate=0.1)})
    traces = [_trace(100, status="error") for _ in range(5)] + [_trace(100) for _ in range(5)]

    alert = monitor.check("router", traces)

    assert alert.level == SLOAlertLevel.BREACHED
    assert any("error rate" in r for r in alert.reasons)


def test_check_reports_both_reasons_when_both_breached():
    monitor = SLOMonitor({"router": SLOThreshold(scope="router", max_p95_latency_ms=100, max_error_rate=0.1)})
    traces = [_trace(2000, status="error") for _ in range(5)] + [_trace(2000) for _ in range(5)]

    alert = monitor.check("router", traces)

    assert alert.level == SLOAlertLevel.BREACHED
    assert len(alert.reasons) == 2


def test_check_unknown_scope_raises():
    monitor = SLOMonitor({})

    with pytest.raises(ValueError):
        monitor.check("unknown", [])


def test_check_with_no_traces_is_a_real_ok_not_fabricated():
    monitor = SLOMonitor({"router": SLOThreshold(scope="router", max_p95_latency_ms=1000, max_error_rate=0.1)})

    alert = monitor.check("router", [])

    assert alert.level == SLOAlertLevel.OK
    assert alert.sample_size == 0
    assert alert.p95_latency_ms == 0.0
    assert alert.error_rate == 0.0
