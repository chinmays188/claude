from datetime import datetime, timezone

import httpx

from app.integrations.github_client import GitHubClient
from app.tools.github_tool import GitHubActivityTool

SINCE = datetime(2026, 1, 1, tzinfo=timezone.utc)
UNTIL = datetime(2026, 1, 31, tzinfo=timezone.utc)


def test_github_tool_returns_summary():
    def handler(request: httpx.Request) -> httpx.Response:
        if "/commits" in str(request.url):
            return httpx.Response(200, json=[{"sha": "abc1234def", "commit": {"message": "Fix bug", "author": {"name": "alice", "date": "2026-01-10T00:00:00Z"}}}])
        return httpx.Response(200, json=[])

    http_client = httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(handler))
    client = GitHubClient(token="fake-token", http_client=http_client)
    tool = GitHubActivityTool(client)

    result = tool.call({"repo": "owner/repo", "since": SINCE.isoformat(), "until": UNTIL.isoformat()})

    assert "Fix bug" in result


def test_github_tool_declares_read_only_permission():
    tool = GitHubActivityTool(GitHubClient(token="x", http_client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=[])))))

    assert tool.permissions == ["read:github"]
