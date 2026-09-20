import pytest
from pydantic import ValidationError

from app.evaluation.human_eval import judge_human_correlation
from app.evaluation.personal_human_eval import PersonalEvalDisplay, PersonalHumanRating


def test_display_carries_all_section_36_fields():
    display = PersonalEvalDisplay(
        case_id="c1", user_request="What am I learning?",
        retrieved_memory=["User is learning Docker."],
        retrieved_documents=["notes.md::chunk0"],
        agent_response="You're learning Docker.",
        citations=["notes.md::chunk0"],
        execution_trace="classifier -> research_agent -> retrieve tool",
    )

    assert display.retrieved_memory == ["User is learning Docker."]
    assert display.execution_trace


def test_rating_average():
    rating = PersonalHumanRating(case_id="c1", correctness=5, personalization=5, trust=5, usefulness=5, citations=5)

    assert rating.average == 5.0


def test_rating_rejects_out_of_range_score():
    with pytest.raises(ValidationError):
        PersonalHumanRating(case_id="c1", correctness=6, personalization=5, trust=5, usefulness=5, citations=5)


def test_reuses_phase1_judge_human_correlation():
    # Section 36: "Compare human scores with LLM-as-judge scores" -- reuses
    # Milestone 11's correlation function rather than reimplementing it.
    correlation = judge_human_correlation([0.1, 0.5, 0.9], [1.0, 3.0, 5.0])

    assert correlation == pytest.approx(1.0)
