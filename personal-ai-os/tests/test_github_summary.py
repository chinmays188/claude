from datetime import datetime, timezone

from app.evaluation.integration_eval import (
    check_correct_repository,
    check_correct_time_period,
    check_no_fabricated_activity,
)
from app.integrations.github_client import CommitSummary, GitHubActivity, PullRequestSummary
from app.integrations.github_summary import summarize_activity

NOW = datetime(2026, 1, 15, tzinfo=timezone.utc)
SINCE = datetime(2026, 1, 1, tzinfo=timezone.utc)
UNTIL = datetime(2026, 1, 31, tzinfo=timezone.utc)


def _activity() -> GitHubActivity:
    return GitHubActivity(
        repo="owner/repo", since=SINCE, until=UNTIL,
        commits=[CommitSummary(sha="abc1234def", message="Fix bug", author="alice", committed_at=NOW)],
        pull_requests=[PullRequestSummary(number=5, title="Add feature", state="closed", created_at=NOW, merged_at=NOW)],
    )


def test_summary_includes_commit_and_pr_details():
    summary = summarize_activity(_activity())

    assert "abc1234" in summary
    assert "Fix bug" in summary
    assert "#5" in summary
    assert "Add feature" in summary


def test_summary_reports_no_activity_when_empty():
    empty = GitHubActivity(repo="owner/repo", since=SINCE, until=UNTIL)

    summary = summarize_activity(empty)

    assert "No activity recorded" in summary


def test_check_correct_repository_passes():
    result = check_correct_repository(_activity(), expected_repo="owner/repo")

    assert result.passed


def test_check_correct_repository_fails():
    result = check_correct_repository(_activity(), expected_repo="other/repo")

    assert not result.passed


def test_check_correct_time_period_passes():
    result = check_correct_time_period(_activity(), expected_since=SINCE, expected_until=UNTIL)

    assert result.passed


def test_check_no_fabricated_activity_passes_for_real_references():
    activity = _activity()
    summary = summarize_activity(activity)

    result = check_no_fabricated_activity(summary, activity)

    assert result.passed


def test_check_no_fabricated_activity_fails_for_invented_pr():
    activity = _activity()
    fabricated_summary = "You also merged #999, a huge refactor."

    result = check_no_fabricated_activity(fabricated_summary, activity)

    assert not result.passed
    assert "#999" in result.reason


def test_check_no_fabricated_activity_fails_for_invented_commit_sha():
    activity = _activity()
    fabricated_summary = "There's also a commit [9999999] that fixed everything."

    result = check_no_fabricated_activity(fabricated_summary, activity)

    assert not result.passed
