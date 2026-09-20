from app.evaluation.regression import MetricSnapshot, RegressionReport, compare


class ReleaseBlockedError(Exception):
    pass


def gate_release(previous: MetricSnapshot, current: MetricSnapshot, tolerance: float = 0.0) -> RegressionReport:
    """Milestone 53: the actual release-blocking check a CI/CD pipeline or a
    manual release script would call before shipping a prompt/model/routing
    change. Reuses Phase 1's regression.compare() (Milestone 11) rather than
    a new comparison implementation — raises ReleaseBlockedError if any
    metric regressed, so a caller can wire this directly into a deploy
    script's exit code."""
    report = compare(previous, current, tolerance=tolerance)
    if report.has_regression:
        regressed_metrics = ", ".join(f"{f.metric} ({f.previous:.3f} -> {f.current:.3f})" for f in report.regressions)
        raise ReleaseBlockedError(f"Release blocked: regression detected in {regressed_metrics}")
    return report
