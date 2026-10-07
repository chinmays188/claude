import httpx
import pytest

from app.integrations.github_git_write_client import GitHubGitWriteClient, GitHubGitWriteError


def test_parse_owner_repo_from_ssh_remote():
    assert GitHubGitWriteClient._parse_owner_repo("git@github.com:chinmays188/linkedin-mcp-server.git") == (
        "chinmays188/linkedin-mcp-server"
    )


def test_parse_owner_repo_without_dot_git_suffix():
    assert GitHubGitWriteClient._parse_owner_repo("git@github.com:chinmays188/linkedin-mcp-server") == (
        "chinmays188/linkedin-mcp-server"
    )


def test_parse_owner_repo_raises_on_unrecognized_remote():
    with pytest.raises(GitHubGitWriteError):
        GitHubGitWriteClient._parse_owner_repo("https://github.com/chinmays188/linkedin-mcp-server.git")


def test_branch_exists_true_on_real_200(monkeypatch):
    client = GitHubGitWriteClient("git@github.com:chinmays188/linkedin-mcp-server.git")

    def fake_get(url, timeout):
        assert "chinmays188/linkedin-mcp-server/branches/some-branch" in url
        return httpx.Response(200, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    assert client.branch_exists("some-branch") is True


def test_branch_exists_false_on_real_404(monkeypatch):
    client = GitHubGitWriteClient("git@github.com:chinmays188/linkedin-mcp-server.git")

    def fake_get(url, timeout):
        return httpx.Response(404, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    assert client.branch_exists("does-not-exist") is False
