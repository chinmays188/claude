import pytest

from app.evaluation.regression import MetricSnapshot
from app.platform.evaluation_gate import ReleaseBlockedError, gate_release


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
