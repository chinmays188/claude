from datetime import datetime, timezone

import httpx
import pytest

from app.integrations.github_client import GitHubApiError, GitHubClient

NOW = datetime(2026, 1, 15, tzinfo=timezone.utc)
SINCE = datetime(2026, 1, 1, tzinfo=timezone.utc)
UNTIL = datetime(2026, 1, 31, tzinfo=timezone.utc)


def _fake_transport(handler) -> httpx.Client:
    return httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(handler))


def test_get_activity_fetches_commits_prs_and_issues():
    def handler(request: httpx.Request) -> httpx.Response:
        if "/commits" in str(request.url):
            return httpx.Response(200, json=[
                {"sha": "abc1234def", "commit": {"message": "Fix bug\n\ndetails", "author": {"name": "alice", "date": "2026-01-10T00:00:00Z"}}}
            ])
        if "/pulls" in str(request.url):
            return httpx.Response(200, json=[
                {"number": 5, "title": "Add feature", "state": "closed", "created_at": "2026-01-05T00:00:00Z", "merged_at": "2026-01-06T00:00:00Z"}
            ])
        if "/issues" in str(request.url):
            return httpx.Response(200, json=[
                {"number": 10, "title": "Bug report", "state": "open", "created_at": "2026-01-08T00:00:00Z"}
            ])
        return httpx.Response(404)

    client = GitHubClient(token="fake-token", http_client=_fake_transport(handler))

    activity = client.get_activity("owner/repo", SINCE, UNTIL)

    assert len(activity.commits) == 1
    assert activity.commits[0].sha == "abc1234def"
    assert len(activity.pull_requests) == 1
    assert activity.pull_requests[0].number == 5
    assert len(activity.issues) == 1
    assert activity.issues[0].number == 10


def test_issues_endpoint_excludes_pull_requests():
    def handler(request: httpx.Request) -> httpx.Response:
        if "/commits" in str(request.url):
            return httpx.Response(200, json=[])
        if "/pulls" in str(request.url):
            return httpx.Response(200, json=[])
        if "/issues" in str(request.url):
            return httpx.Response(200, json=[
                {"number": 1, "title": "Real issue", "state": "open", "created_at": "2026-01-08T00:00:00Z"},
                {"number": 2, "title": "Actually a PR", "state": "open", "created_at": "2026-01-08T00:00:00Z", "pull_request": {}},
            ])
        return httpx.Response(404)

    client = GitHubClient(token="fake-token", http_client=_fake_transport(handler))

    activity = client.get_activity("owner/repo", SINCE, UNTIL)

    assert len(activity.issues) == 1
    assert activity.issues[0].number == 1


def test_pull_requests_filtered_by_time_period():
    def handler(request: httpx.Request) -> httpx.Response:
        if "/commits" in str(request.url):
            return httpx.Response(200, json=[])
        if "/pulls" in str(request.url):
            return httpx.Response(200, json=[
                {"number": 1, "title": "In range", "state": "open", "created_at": "2026-01-15T00:00:00Z", "merged_at": None},
                {"number": 2, "title": "Out of range", "state": "open", "created_at": "2025-06-01T00:00:00Z", "merged_at": None},
            ])
        if "/issues" in str(request.url):
            return httpx.Response(200, json=[])
        return httpx.Response(404)

    client = GitHubClient(token="fake-token", http_client=_fake_transport(handler))

    activity = client.get_activity("owner/repo", SINCE, UNTIL)

    assert len(activity.pull_requests) == 1
    assert activity.pull_requests[0].number == 1


def test_api_error_raises_github_api_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    client = GitHubClient(token="fake-token", http_client=_fake_transport(handler))

    with pytest.raises(GitHubApiError):
        client.get_activity("owner/repo", SINCE, UNTIL)
