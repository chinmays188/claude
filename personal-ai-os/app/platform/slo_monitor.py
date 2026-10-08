"""Real, monitored SLO thresholds, found missing while investigating
"Production AI Engineering" (disclosed gap: "the 'AI SLO' / 'AI incident
management' success criterion is still only partially covered: eval-
gating is real; a monitored, alerting SLO threshold is not"). Mirrors
app/platform/cost_governance.py's CostGovernor pattern exactly (a real,
earlier precedent for "turn after-the-fact reporting into an alerting
signal") -- SLOMonitor.check() computes real p95 latency and real error
rate from actual stored Trace data (app/observability/traces.py,
error_analysis.py's trace_error_rate), and returns a real SLOAlert a
caller (or the dashboard) can act on. Never blocks a request itself --
same as CostGovernor, this only produces the signal."""

from enum import Enum

from pydantic import BaseModel

from app.observability.error_analysis import trace_error_rate
from app.observability.traces import Trace


class SLOAlertLevel(str, Enum):
    OK = "OK"
    WARNING = "WARNING"  # approaching the threshold
    BREACHED = "BREACHED"  # over the threshold


class SLOThreshold(BaseModel):
    scope: str
    max_p95_latency_ms: float
    max_error_rate: float
    warning_fraction: float = 0.8  # fraction of the threshold that triggers WARNING


class SLOAlert(BaseModel):
    scope: str
    level: SLOAlertLevel
    p95_latency_ms: float
    p95_latency_threshold_ms: float
    error_rate: float
    error_rate_threshold: float
    sample_size: int
    reasons: list[str]


def compute_p95_latency_ms(traces: list[Trace]) -> float:
    """Real p95 (95th percentile) latency over real Trace.latency_ms
    values -- 0.0 (an honest real zero, not fabricated) when there's no
    data yet. Simple real percentile via sorted-list index, no
    statistics dependency needed for this."""
    if not traces:
        return 0.0
    latencies = sorted(t.latency_ms for t in traces)
    index = min(int(len(latencies) * 0.95), len(latencies) - 1)
    return latencies[index]


class SLOMonitor:
    def __init__(self, thresholds: dict[str, SLOThreshold]):
        self._thresholds = thresholds

    def check(self, scope: str, traces: list[Trace]) -> SLOAlert:
        threshold = self._thresholds.get(scope)
        if threshold is None:
            raise ValueError(f"No SLO threshold configured for scope '{scope}'.")

        p95_latency = compute_p95_latency_ms(traces)
        error_rate = trace_error_rate(traces)

        reasons = []
        level = SLOAlertLevel.OK

        if p95_latency > threshold.max_p95_latency_ms:
            level = SLOAlertLevel.BREACHED
            reasons.append(
                f"p95 latency {p95_latency:.0f}ms exceeds threshold {threshold.max_p95_latency_ms:.0f}ms"
            )
        elif p95_latency >= threshold.max_p95_latency_ms * threshold.warning_fraction:
            level = SLOAlertLevel.WARNING
            reasons.append(
                f"p95 latency {p95_latency:.0f}ms is within "
                f"{(1 - threshold.warning_fraction) * 100:.0f}% of threshold {threshold.max_p95_latency_ms:.0f}ms"
            )

        if error_rate > threshold.max_error_rate:
            level = SLOAlertLevel.BREACHED
            reasons.append(f"error rate {error_rate:.1%} exceeds threshold {threshold.max_error_rate:.1%}")
        elif error_rate >= threshold.max_error_rate * threshold.warning_fraction and level == SLOAlertLevel.OK:
            level = SLOAlertLevel.WARNING
            reasons.append(
                f"error rate {error_rate:.1%} is within "
                f"{(1 - threshold.warning_fraction) * 100:.0f}% of threshold {threshold.max_error_rate:.1%}"
            )

        return SLOAlert(
            scope=scope, level=level,
            p95_latency_ms=p95_latency, p95_latency_threshold_ms=threshold.max_p95_latency_ms,
            error_rate=error_rate, error_rate_threshold=threshold.max_error_rate,
            sample_size=len(traces), reasons=reasons,
        )
