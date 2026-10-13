from app.evaluation.confidence import SignificanceResult, compare_pass_rates
from app.evaluation.regression import MetricSnapshot, RegressionReport, compare


class ReleaseBlockedError(Exception):
    pass


def gate_release(previous: MetricSnapshot, current: MetricSnapshot, tolerance: float = 0.0) -> RegressionReport:
    """Milestone 53: the actual release-blocking check a CI/CD pipeline or a
    manual release script would call before shipping a prompt/model/routing
    change. Reuses Phase 1's regression.compare() (Milestone 11) rather than
    a new comparison implementation — raises ReleaseBlockedError if any
    metric regressed, so a caller can wire this directly into a deploy
    script's exit code.

    Deliberately kept as the single-run point comparison it always was --
    correct for a real point-value metric with no sampling distribution
    (e.g. real dollar cost, a fixed latency reading). For a PASS-RATE
    metric (a real golden-set accuracy, genuinely noisy across runs since
    this project's LLM calls aren't perfectly deterministic), use
    gate_release_significance() below instead, which requires the delta's
    confidence interval to actually exclude 0 before calling it a real
    regression or improvement."""
    report = compare(previous, current, tolerance=tolerance)
    if report.has_regression:
        regressed_metrics = ", ".join(f"{f.metric} ({f.previous:.3f} -> {f.current:.3f})" for f in report.regressions)
        raise ReleaseBlockedError(f"Release blocked: regression detected in {regressed_metrics}")
    return report


def gate_release_significance(
    previous_successes: int, previous_n: int, current_successes: int, current_n: int, confidence: float = 0.95,
) -> SignificanceResult:
    """Real significance-gated release check for a pass-rate metric, found
    missing after the user shared an eval-methodology excerpt: 'the
    performance delta CI must be statistically significant. An interval
    is inconclusive if it contains 0.' This project's existing
    gate_release() would call a single-run 0.85 -> 0.90 delta a real
    improvement with zero regard for whether that's distinguishable from
    noise; this function only ever calls REGRESSION/IMPROVEMENT when the
    real confidence interval on the delta excludes 0 -- otherwise it
    raises for a different, honestly-labeled reason (not enough evidence
    either way), rather than silently blocking OR silently shipping."""
    result = compare_pass_rates(previous_successes, previous_n, current_successes, current_n, confidence=confidence)

    if result.verdict == "REGRESSION":
        raise ReleaseBlockedError(
            f"Release blocked: statistically significant regression detected "
            f"(delta {result.delta_point_estimate:+.3f}, 95% CI [{result.delta_lower:.3f}, {result.delta_upper:.3f}])."
        )
    if result.verdict == "INCONCLUSIVE":
        raise ReleaseBlockedError(
            f"Release blocked: not enough evidence to call this an improvement or a regression "
            f"(delta {result.delta_point_estimate:+.3f}, 95% CI [{result.delta_lower:.3f}, {result.delta_upper:.3f}] "
            f"includes 0). Run more eval samples before deciding."
        )
    return result
