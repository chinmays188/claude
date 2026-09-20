from app.domains.career.models import JdAnalysisResult
from app.evaluation.career_eval import check_jd_analysis_scores_in_range


def _result(overall=0.5) -> JdAnalysisResult:
    return JdAnalysisResult(
        overall_fit=overall, technical_fit=0.5, ai_fit=0.5, pm_fit=0.5, domain_fit=0.5, leadership_fit=0.5,
    )


def test_scores_in_range_passes():
    result = check_jd_analysis_scores_in_range(_result())

    assert result.passed


def test_scores_out_of_range_fails():
    result = check_jd_analysis_scores_in_range(_result(overall=1.5))

    assert not result.passed
    assert "overall_fit" in result.reason
