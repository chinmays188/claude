import pytest

from app.evaluation.regression import MetricSnapshot
from app.platform.evaluation_gate import ReleaseBlockedError, gate_release, gate_release_significance


def test_gate_release_passes_when_no_regression():
    previous = MetricSnapshot(version="0.4", metrics={"task_completion": 0.90})
    current = MetricSnapshot(version="0.5", metrics={"task_completion": 0.92})

    report = gate_release(previous, current)

    assert not report.has_regression


def test_gate_release_blocks_on_regression():
    previous = MetricSnapshot(version="0.4", metrics={"groundedness": 0.94})
    current = MetricSnapshot(version="0.5", metrics={"groundedness": 0.85})

    with pytest.raises(ReleaseBlockedError):
        gate_release(previous, current)


def test_gate_release_blocks_even_if_another_metric_improved():
    previous = MetricSnapshot(version="0.4", metrics={"task_completion": 0.90, "groundedness": 0.94})
    current = MetricSnapshot(version="0.5", metrics={"task_completion": 0.95, "groundedness": 0.85})

    with pytest.raises(ReleaseBlockedError):
        gate_release(previous, current)


def test_gate_release_significance_passes_through_a_real_significant_improvement():
    result = gate_release_significance(
        previous_successes=50, previous_n=100, current_successes=95, current_n=100,
    )

    assert result.verdict == "IMPROVEMENT"


def test_gate_release_significance_blocks_a_real_significant_regression():
    with pytest.raises(ReleaseBlockedError, match="regression"):
        gate_release_significance(
            previous_successes=95, previous_n=100, current_successes=50, current_n=100,
        )


def test_gate_release_significance_blocks_an_inconclusive_result_with_a_distinct_message():
    """The real point of this function: a tiny golden set with a small,
    single-run-sized delta must NOT be silently approved as a real
    improvement -- it should block for an honestly different reason
    (not enough evidence), distinguishable from a real regression."""
    with pytest.raises(ReleaseBlockedError, match="not enough evidence"):
        gate_release_significance(
            previous_successes=4, previous_n=5, current_successes=5, current_n=5,
        )
