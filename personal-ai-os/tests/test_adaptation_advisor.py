import pytest

from app.evaluation.adaptation_advisor import (
    AdaptationApproach,
    AdaptationProblem,
    recommend_approach,
)


def test_fresh_external_knowledge_recommends_rag():
    problem = AdaptationProblem(needs_fresh_external_knowledge=True)

    assert recommend_approach(problem) == AdaptationApproach.RAG


def test_specific_output_style_recommends_fine_tuning():
    problem = AdaptationProblem(needs_specific_output_style_or_format=True)

    assert recommend_approach(problem) == AdaptationApproach.FINE_TUNING


def test_simple_example_solvable_recommends_icl():
    problem = AdaptationProblem(is_simple_and_example_solvable=True)

    assert recommend_approach(problem) == AdaptationApproach.IN_CONTEXT_LEARNING


def test_smaller_model_matching_larger_recommends_distillation():
    problem = AdaptationProblem(needs_smaller_model_to_match_larger_model=True)

    assert recommend_approach(problem) == AdaptationApproach.DISTILLATION


def test_no_signal_raises_rather_than_guessing():
    problem = AdaptationProblem()

    with pytest.raises(ValueError):
        recommend_approach(problem)


def test_distillation_signal_takes_priority_when_multiple_match():
    problem = AdaptationProblem(
        needs_fresh_external_knowledge=True,
        needs_smaller_model_to_match_larger_model=True,
    )

    assert recommend_approach(problem) == AdaptationApproach.DISTILLATION
