from app.evaluation.voice_eval import InteractionResult, compare_interactions


def test_compares_task_completion_rates_by_mode():
    results = [
        InteractionResult(mode="voice", task_completed=True, latency_ms=1000),
        InteractionResult(mode="voice", task_completed=False, latency_ms=1200),
        InteractionResult(mode="text", task_completed=True, latency_ms=500),
        InteractionResult(mode="text", task_completed=True, latency_ms=600),
    ]

    comparison = compare_interactions(results)

    assert comparison.voice_task_completion_rate == 0.5
    assert comparison.text_task_completion_rate == 1.0


def test_compares_average_latency_by_mode():
    results = [
        InteractionResult(mode="voice", task_completed=True, latency_ms=1000),
        InteractionResult(mode="voice", task_completed=True, latency_ms=2000),
        InteractionResult(mode="text", task_completed=True, latency_ms=400),
    ]

    comparison = compare_interactions(results)

    assert comparison.voice_avg_latency_ms == 1500
    assert comparison.text_avg_latency_ms == 400


def test_compares_correction_rate_by_mode():
    results = [
        InteractionResult(mode="voice", task_completed=True, latency_ms=1000, correction_needed=True),
        InteractionResult(mode="voice", task_completed=True, latency_ms=1000, correction_needed=False),
        InteractionResult(mode="text", task_completed=True, latency_ms=1000, correction_needed=False),
    ]

    comparison = compare_interactions(results)

    assert comparison.voice_correction_rate == 0.5
    assert comparison.text_correction_rate == 0.0


def test_empty_results_do_not_crash():
    comparison = compare_interactions([])

    assert comparison.voice_task_completion_rate == 0.0
    assert comparison.text_task_completion_rate == 0.0
