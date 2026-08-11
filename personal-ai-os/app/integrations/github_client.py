from datetime import datetime

import httpx
from pydantic import BaseModel


class GitHubApiError(Exception):
    pass


class CommitSummary(BaseModel):
    sha: str
    message: str
    author: str
    committed_at: datetime


class PullRequestSummary(BaseModel):
    number: int
    title: str
    state: str
    created_at: datetime
    merged_at: datetime | None = None


class IssueSummary(BaseModel):
    number: int
    title: str
    state: str
    created_at: datetime


class GitHubActivity(BaseModel):
    repo: str
    since: datetime
    until: datetime
    commits: list[CommitSummary] = []
    pull_requests: list[PullRequestSummary] = []
    issues: list[IssueSummary] = []


class GitHubClient:
    """Read-only GitHub REST API client. Section 22: 'Start with read-only
    integrations' — no write/mutate methods exist on this class at all, so
    there is no accidental-write surface to guard against."""

    def __init__(self, token: str, base_url: str = "https://api.github.com", http_client: httpx.Client | None = None):
        self._http = http_client or httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=10.0,
        )

    def get_activity(self, repo: str, since: datetime, until: datetime) -> GitHubActivity:
        commits = self._get_commits(repo, since, until)
        pull_requests = self._get_pull_requests(repo, since, until)
        issues = self._get_issues(repo, since, until)
        return GitHubActivity(repo=repo, since=since, until=until, commits=commits, pull_requests=pull_requests, issues=issues)

    def _get_commits(self, repo: str, since: datetime, until: datetime) -> list[CommitSummary]:
        response = self._http.get(
            f"/repos/{repo}/commits",
            params={"since": since.isoformat(), "until": until.isoformat()},
        )
        self._raise_for_status(response)
        return [
            CommitSummary(
                sha=c["sha"],
                message=c["commit"]["message"],
                author=c["commit"]["author"]["name"],
                committed_at=datetime.fromisoformat(c["commit"]["author"]["date"].replace("Z", "+00:00")),
            )
            for c in response.json()
        ]

    def _get_pull_requests(self, repo: str, since: datetime, until: datetime) -> list[PullRequestSummary]:
        response = self._http.get(f"/repos/{repo}/pulls", params={"state": "all"})
        self._raise_for_status(response)
        results = []
        for pr in response.json():
            created_at = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
            if not (since <= created_at <= until):
                continue
            merged_at = pr["merged_at"]
            results.append(
                PullRequestSummary(
                    number=pr["number"], title=pr["title"], state=pr["state"],
                    created_at=created_at,
                    merged_at=datetime.fromisoformat(merged_at.replace("Z", "+00:00")) if merged_at else None,
                )
            )
        return results

    def _get_issues(self, repo: str, since: datetime, until: datetime) -> list[IssueSummary]:
        response = self._http.get(f"/repos/{repo}/issues", params={"state": "all", "since": since.isoformat()})
        self._raise_for_status(response)
        results = []
        for issue in response.json():
            if "pull_request" in issue:
                continue  # GitHub's issues endpoint also returns PRs; exclude them
            created_at = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
            if not (since <= created_at <= until):
                continue
            results.append(IssueSummary(number=issue["number"], title=issue["title"], state=issue["state"], created_at=created_at))
        return results

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            raise GitHubApiError(f"GitHub API error {response.status_code}: {response.text}")
