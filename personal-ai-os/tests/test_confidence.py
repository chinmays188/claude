import pytest

from app.evaluation.confidence import ConfidenceInterval, compare_pass_rates, wilson_interval


def test_wilson_interval_point_estimate_matches_simple_proportion():
    ci = wilson_interval(successes=5, n=10)

    assert ci.point_estimate == 0.5
    assert ci.n == 10


def test_wilson_interval_stays_within_0_and_1_bounds():
    ci = wilson_interval(successes=5, n=5)  # a real 100% pass rate on a tiny golden set

    assert 0.0 <= ci.lower <= 1.0
    assert 0.0 <= ci.upper <= 1.0
    assert ci.upper == 1.0  # a perfect run should allow the upper bound to reach 1.0


def test_wilson_interval_narrows_with_more_trials():
    """Real statistical property: the same observed proportion (50%)
    should have a WIDER interval from fewer trials than from more --
    more evidence means more certainty."""
    narrow = wilson_interval(successes=50, n=100)
    wide = wilson_interval(successes=5, n=10)

    assert (narrow.upper - narrow.lower) < (wide.upper - wide.lower)


def test_wilson_interval_rejects_invalid_n():
    with pytest.raises(ValueError):
        wilson_interval(successes=1, n=0)


def test_wilson_interval_rejects_successes_exceeding_n():
    with pytest.raises(ValueError):
        wilson_interval(successes=11, n=10)


def test_excludes_zero_true_when_fully_positive():
    ci = ConfidenceInterval(point_estimate=0.5, lower=0.1, upper=0.9, n=10)
    assert ci.excludes_zero() is True


def test_excludes_zero_false_when_interval_spans_zero():
    ci = ConfidenceInterval(point_estimate=0.0, lower=-0.1, upper=0.1, n=10)
    assert ci.excludes_zero() is False


def test_identical_pass_rates_are_inconclusive_not_improvement():
    """Two identical runs should never be called an improvement or
    regression -- the delta point estimate is exactly 0."""
    result = compare_pass_rates(previous_successes=8, previous_n=10, current_successes=8, current_n=10)

    assert result.verdict == "INCONCLUSIVE"
    assert result.is_significant is False


def test_small_single_run_delta_is_inconclusive_not_a_real_improvement():
    """The real scenario this module exists to catch: a tiny golden set
    (5 cases), one run before and one run after, with a 1-case
    improvement -- nowhere near enough evidence to call this a real,
    statistically significant improvement, even though the raw point
    estimate went up."""
    result = compare_pass_rates(previous_successes=4, previous_n=5, current_successes=5, current_n=5)

    assert result.verdict == "INCONCLUSIVE"


def test_large_consistent_improvement_is_significant():
    """A real, large, consistently-replicated improvement (e.g. 50/100
    passes before, 95/100 after) should be large enough to be called a
    genuine, statistically significant improvement."""
    result = compare_pass_rates(previous_successes=50, previous_n=100, current_successes=95, current_n=100)

    assert result.verdict == "IMPROVEMENT"
    assert result.is_significant is True


def test_large_consistent_regression_is_significant():
    result = compare_pass_rates(previous_successes=95, previous_n=100, current_successes=50, current_n=100)

    assert result.verdict == "REGRESSION"
