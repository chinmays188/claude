import pytest

from app.evaluation.domain_golden import count_cases_by_domain, load_domain_cases


def test_load_career_cases():
    cases = load_domain_cases("career")

    assert len(cases) > 0
    assert all(c.id.startswith("career_") for c in cases)


def test_load_cross_domain_cases_have_expected_domains():
    cases = load_domain_cases("cross_domain")

    assert len(cases) > 0
    assert all(c.expected_domains for c in cases)


def test_load_missing_domain_raises():
    with pytest.raises(FileNotFoundError):
        load_domain_cases("nonexistent_domain")


def test_count_cases_by_domain_covers_all_five():
    counts = count_cases_by_domain()

    assert set(counts.keys()) == {"career", "pm", "finance", "learning", "cross_domain"}
    assert all(n > 0 for n in counts.values())
