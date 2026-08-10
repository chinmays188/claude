import pytest
from pydantic import ValidationError

from app.evaluation.human_eval import HumanRating, judge_human_correlation


def test_human_rating_average():
    rating = HumanRating(
        case_id="c1", correctness=5, relevance=5, completeness=5,
        trustworthiness=5, usefulness=5, citation_quality=5,
    )

    assert rating.average == 5.0


def test_human_rating_rejects_out_of_range_score():
    with pytest.raises(ValidationError):
        HumanRating(
            case_id="c1", correctness=6, relevance=5, completeness=5,
            trustworthiness=5, usefulness=5, citation_quality=5,
        )


def test_perfect_positive_correlation():
    judge_scores = [0.1, 0.5, 0.9]
    human_scores = [1.0, 3.0, 5.0]

    correlation = judge_human_correlation(judge_scores, human_scores)

    assert correlation == pytest.approx(1.0)


def test_no_correlation_with_constant_scores():
    judge_scores = [0.5, 0.5, 0.5]
    human_scores = [1.0, 3.0, 5.0]

    correlation = judge_human_correlation(judge_scores, human_scores)

    assert correlation == 0.0


def test_mismatched_lengths_raise():
    with pytest.raises(ValueError):
        judge_human_correlation([0.1, 0.2], [1.0])


def test_too_few_points_raise():
    with pytest.raises(ValueError):
        judge_human_correlation([0.1], [1.0])
