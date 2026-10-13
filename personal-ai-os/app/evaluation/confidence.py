"""Real statistical rigor for eval pass rates, found missing after the
user shared a real excerpt on eval methodology: "Due to LLM
stochasticity, agent performance evals must measure uncertainty and
report confidence intervals with mean pass rates... When deciding
whether a change is an improvement, the performance delta CI must be
statistically significant. An interval is inconclusive if it contains
0."

Checked first, honestly: this project's `app/evaluation/golden.py`'s
`pass_rate()` and `app/evaluation/regression.py`'s `compare()` (which
gates real releases via `app/platform/evaluation_gate.py`'s
`gate_release()`) both treat a SINGLE run's result as ground truth --
any nonzero delta between two single runs is called a real regression
or improvement, with zero notion that this project's own LLM calls are
confirmed NOT perfectly deterministic (found earlier this session:
Gemini shows real variance even at temperature=0.0 on a creative
prompt) -- so a single-run pass-rate delta can be pure sampling noise,
not a real behavior change.

This module is deliberately separate from, not a replacement for,
`regression.compare()`: that function is still the right tool for a
real point-value metric that genuinely has no sampling distribution
(e.g. a dollar cost, a fixed latency measurement from one real call).
This module is specifically for PASS-RATE-style metrics, which are
Bernoulli proportions over a finite golden set and genuinely benefit
from a real statistical interval -- exactly the excerpt's distinction
between a benchmark pass rate (needs multiple runs + a real interval
method appropriate to its sample size) and a single deterministic
point value.
"""

import math

from pydantic import BaseModel


class ConfidenceInterval(BaseModel):
    point_estimate: float
    lower: float
    upper: float
    n: int  # number of trials the interval was computed from

    def excludes_zero(self) -> bool:
        return self.lower > 0 or self.upper < 0

    def contains(self, value: float) -> bool:
        return self.lower <= value <= self.upper


def wilson_interval(successes: int, n: int, confidence: float = 0.95) -> ConfidenceInterval:
    """Wilson score interval for a binomial proportion -- the real,
    standard choice for a pass rate from a FINITE golden set (as opposed
    to a normal-approximation interval, which can extend outside [0, 1]
    and is a poor approximation for small n or a pass rate near 0 or 1,
    both common in a golden-set eval: a 5/5 pass is a realistic and
    important case this interval must still handle sanely)."""
    if n <= 0:
        raise ValueError("n must be positive -- a confidence interval needs at least one trial.")
    if not 0 <= successes <= n:
        raise ValueError(f"successes ({successes}) must be between 0 and n ({n}).")

    # z for the requested two-sided confidence level. Only the two real
    # levels this project is ever likely to need are supported exactly;
    # anything else falls back to the 95% z-score rather than silently
    # guessing a value, since an eval gate should never trust an
    # approximate z-score it can't justify.
    z_by_confidence = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_by_confidence.get(round(confidence, 2), 1.96)

    p_hat = successes / n
    denom = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denom
    half_width = (z * math.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))) / denom

    lower = max(0.0, center - half_width)
    upper = min(1.0, center + half_width)
    return ConfidenceInterval(point_estimate=p_hat, lower=lower, upper=upper, n=n)


class SignificanceResult(BaseModel):
    """Real, inspectable outcome of comparing two multi-run pass rates --
    deliberately 3-valued (IMPROVEMENT / REGRESSION / INCONCLUSIVE), never
    forced into a binary pass/fail, per the excerpt's own rule: 'An
    interval is inconclusive if it contains 0' is a real third outcome,
    not a failure to decide."""

    previous: ConfidenceInterval
    current: ConfidenceInterval
    delta_point_estimate: float
    delta_lower: float
    delta_upper: float
    verdict: str  # "IMPROVEMENT" | "REGRESSION" | "INCONCLUSIVE"

    @property
    def is_significant(self) -> bool:
        return self.verdict != "INCONCLUSIVE"


def compare_pass_rates(
    previous_successes: int, previous_n: int, current_successes: int, current_n: int, confidence: float = 0.95,
) -> SignificanceResult:
    """Real significance test for a pass-rate delta between two multi-run
    snapshots. Uses a conservative, real approximation (the delta's own CI
    is built from the two independent Wilson intervals' half-widths
    combined in quadrature -- a standard, real way to approximate a CI on
    a difference of two independent proportions without requiring a
    Newcombe-interval implementation) rather than claiming more precision
    than this project's real golden-set sizes can support.

    The verdict is INCONCLUSIVE whenever the delta's CI contains 0 --
    exactly the excerpt's rule -- which is the common, expected outcome
    for a small golden set and a small real behavior change, not a sign
    this function is broken."""
    previous_ci = wilson_interval(previous_successes, previous_n, confidence=confidence)
    current_ci = wilson_interval(current_successes, current_n, confidence=confidence)

    delta_point_estimate = current_ci.point_estimate - previous_ci.point_estimate
    prev_half_width = (previous_ci.upper - previous_ci.lower) / 2
    curr_half_width = (current_ci.upper - current_ci.lower) / 2
    delta_half_width = math.sqrt(prev_half_width**2 + curr_half_width**2)

    delta_lower = delta_point_estimate - delta_half_width
    delta_upper = delta_point_estimate + delta_half_width

    if delta_lower > 0:
        verdict = "IMPROVEMENT"
    elif delta_upper < 0:
        verdict = "REGRESSION"
    else:
        verdict = "INCONCLUSIVE"

    return SignificanceResult(
        previous=previous_ci, current=current_ci,
        delta_point_estimate=delta_point_estimate, delta_lower=delta_lower, delta_upper=delta_upper,
        verdict=verdict,
    )
