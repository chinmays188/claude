from pydantic import BaseModel

from app.integrations.github_client import GitHubActivity


class IntegrationCheckResult(BaseModel):
    name: str
    passed: bool
    reason: str


def check_correct_repository(activity: GitHubActivity, expected_repo: str) -> IntegrationCheckResult:
    passed = activity.repo == expected_repo
    return IntegrationCheckResult(
        name="correct_repository", passed=passed,
        reason="Matches expected repo." if passed else f"Expected '{expected_repo}', got '{activity.repo}'.",
    )


def check_correct_time_period(activity: GitHubActivity, expected_since, expected_until) -> IntegrationCheckResult:
    passed = activity.since == expected_since and activity.until == expected_until
    return IntegrationCheckResult(
        name="correct_time_period", passed=passed,
        reason="Matches expected window." if passed else "Time window does not match expected range.",
    )


def check_no_fabricated_activity(summary_text: str, activity: GitHubActivity) -> IntegrationCheckResult:
    """Section 23: 'No fabricated activity.' Verifies every commit sha / PR
    number / issue number mentioned in the summary actually exists in the raw
    fetched activity — catches an LLM inventing a plausible-sounding commit or
    PR that was never actually returned by the API."""
    real_shas = {c.sha[:7] for c in activity.commits}
    real_pr_numbers = {f"#{pr.number}" for pr in activity.pull_requests}
    real_issue_numbers = {f"#{i.number}" for i in activity.issues}

    import re
    mentioned_shas = set(re.findall(r"\[([0-9a-f]{7})\]", summary_text))
    mentioned_numbers = set(re.findall(r"#\d+", summary_text))

    fabricated_shas = mentioned_shas - real_shas
    fabricated_numbers = mentioned_numbers - real_pr_numbers - real_issue_numbers

    if fabricated_shas or fabricated_numbers:
        return IntegrationCheckResult(
            name="no_fabricated_activity", passed=False,
            reason=f"Summary references non-existent items: shas={fabricated_shas}, numbers={fabricated_numbers}",
        )
    return IntegrationCheckResult(name="no_fabricated_activity", passed=True, reason="All referenced items are real.")
