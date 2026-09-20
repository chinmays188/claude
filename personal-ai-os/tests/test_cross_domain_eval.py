from app.domains.cross_domain.advisor import CrossDomainRecommendation, DomainPerspective
from app.domains.router import Domain
from app.evaluation.cross_domain_eval import (
    check_all_expected_perspectives_present,
    check_correct_domain_selection,
    check_reasoning_references_perspectives,
)


def test_correct_domain_selection_passes_for_exact_match():
    result = check_correct_domain_selection([Domain.CAREER, Domain.LEARNING], {Domain.CAREER, Domain.LEARNING})

    assert result.passed


def test_correct_domain_selection_fails_for_missing_domain():
    result = check_correct_domain_selection([Domain.CAREER], {Domain.CAREER, Domain.LEARNING})

    assert not result.passed


def test_correct_domain_selection_fails_for_extra_domain():
    result = check_correct_domain_selection([Domain.CAREER, Domain.LEARNING, Domain.PM], {Domain.CAREER, Domain.LEARNING})

    assert not result.passed


def test_all_expected_perspectives_present_passes():
    perspectives = [DomainPerspective(domain="CAREER", perspective="x"), DomainPerspective(domain="LEARNING", perspective="y")]

    result = check_all_expected_perspectives_present(perspectives, {"CAREER", "LEARNING"})

    assert result.passed


def test_all_expected_perspectives_present_fails_when_missing():
    perspectives = [DomainPerspective(domain="CAREER", perspective="x")]

    result = check_all_expected_perspectives_present(perspectives, {"CAREER", "LEARNING"})

    assert not result.passed
    assert "LEARNING" in result.reason


def test_reasoning_references_perspectives_passes():
    perspectives = [DomainPerspective(domain="CAREER", perspective="Kubernetes appears frequently in target job descriptions.")]
    recommendation = CrossDomainRecommendation(
        career_relevance="HIGH", current_work_relevance="MEDIUM", learning_difficulty="HIGH",
        recommended_priority="MEDIUM", reasoning="Kubernetes appears frequently in job descriptions for target roles.",
    )

    result = check_reasoning_references_perspectives(recommendation, perspectives)

    assert result.passed


def test_reasoning_references_perspectives_fails_when_disconnected():
    perspectives = [DomainPerspective(domain="CAREER", perspective="Kubernetes appears frequently in target job descriptions.")]
    recommendation = CrossDomainRecommendation(
        career_relevance="HIGH", current_work_relevance="MEDIUM", learning_difficulty="HIGH",
        recommended_priority="MEDIUM", reasoning="Sounds good, go for it.",
    )

    result = check_reasoning_references_perspectives(recommendation, perspectives)

    assert not result.passed
