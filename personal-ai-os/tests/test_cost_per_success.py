from app.observability.cost_per_success import compute_cost_per_success


def test_computes_cost_per_success_and_per_failure():
    summaries = [
        {"status": "success", "cost": 0.01},
        {"status": "success", "cost": 0.03},
        {"status": "error", "cost": 0.02},
    ]

    report = compute_cost_per_success(summaries)

    assert report.successful_count == 2
    assert report.failed_count == 1
    assert report.cost_per_success == 0.02  # (0.01 + 0.03) / 2
    assert report.cost_per_failure == 0.02
    assert report.total_cost == 0.06


def test_success_rate():
    summaries = [{"status": "success", "cost": 0.0}, {"status": "error", "cost": 0.0}, {"status": "error", "cost": 0.0}]

    report = compute_cost_per_success(summaries)

    assert report.success_rate == 1 / 3


def test_empty_summaries_returns_none_not_zero():
    report = compute_cost_per_success([])

    assert report.cost_per_success is None
    assert report.cost_per_failure is None
    assert report.success_rate is None
    assert report.total_cost == 0.0


def test_no_failures_yet_cost_per_failure_is_none():
    summaries = [{"status": "success", "cost": 0.05}]

    report = compute_cost_per_success(summaries)

    assert report.cost_per_success == 0.05
    assert report.cost_per_failure is None


def test_missing_cost_key_treated_as_zero():
    summaries = [{"status": "success"}]

    report = compute_cost_per_success(summaries)

    assert report.cost_per_success == 0.0
