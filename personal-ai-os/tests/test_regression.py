from app.evaluation.regression import MetricSnapshot, compare


def test_no_change_no_regression_no_improvement():
    prev = MetricSnapshot(version="0.4", metrics={"task_completion": 0.91})
    curr = MetricSnapshot(version="0.5", metrics={"task_completion": 0.91})

    report = compare(prev, curr)

    assert not report.has_regression
    assert report.improvements == []


def test_metric_drop_flagged_as_regression():
    prev = MetricSnapshot(version="0.4", metrics={"groundedness": 0.94})
    curr = MetricSnapshot(version="0.5", metrics={"groundedness": 0.87})

    report = compare(prev, curr)

    assert report.has_regression
    assert report.regressions[0].metric == "groundedness"
    assert report.regressions[0].delta < 0


def test_one_metric_up_another_down_still_flags_regression():
    """Section 14: an improvement on one metric doesn't excuse a regression on another."""
    prev = MetricSnapshot(version="0.4", metrics={"task_completion": 0.91, "citation_quality": 0.90})
    curr = MetricSnapshot(version="0.5", metrics={"task_completion": 0.94, "citation_quality": 0.82})

    report = compare(prev, curr)

    assert report.has_regression
    assert len(report.improvements) == 1
    assert len(report.regressions) == 1


def test_metrics_only_in_one_snapshot_are_ignored():
    prev = MetricSnapshot(version="0.4", metrics={"a": 0.5})
    curr = MetricSnapshot(version="0.5", metrics={"a": 0.5, "b": 0.9})

    report = compare(prev, curr)

    assert not report.has_regression
    assert report.improvements == []


def test_tolerance_absorbs_small_noise():
    prev = MetricSnapshot(version="0.4", metrics={"a": 0.900})
    curr = MetricSnapshot(version="0.5", metrics={"a": 0.895})

    report = compare(prev, curr, tolerance=0.01)

    assert not report.has_regression
