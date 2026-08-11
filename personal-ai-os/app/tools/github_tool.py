from datetime import datetime

from pydantic import BaseModel

from app.integrations.github_client import GitHubApiError, GitHubClient
from app.integrations.github_summary import summarize_activity
from app.tools.base import Tool, ToolError


class GitHubActivityArgs(BaseModel):
    repo: str
    since: datetime
    until: datetime


class GitHubActivityTool(Tool):
    name = "github_activity"
    description = (
        "Fetch a summary of GitHub activity (commits, pull requests, issues) for a "
        "repository within a date range. Use this for questions like 'what did I "
        "accomplish on this project this week?'"
    )
    args_schema = GitHubActivityArgs
    permissions = ["read:github"]
    retry_safe = True

    def __init__(self, client: GitHubClient):
        self._client = client

    def run(self, args: GitHubActivityArgs) -> str:
        try:
            activity = self._client.get_activity(args.repo, args.since, args.until)
        except GitHubApiError as exc:
            raise ToolError(f"GitHub activity fetch failed: {exc}") from exc
        return summarize_activity(activity)
