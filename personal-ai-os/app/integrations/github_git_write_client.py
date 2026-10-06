"""Real, live write access to a GitHub repo via git-over-SSH, not the REST
API. Built while investigating "Human-in-the-Loop AI" after a real
constraint was found: GitHubClient (github_client.py) only ever makes
REST calls needing a Bearer token, and no GITHUB_TOKEN/GH_TOKEN is
configured in this environment. SSH push access to a real scratch repo
(chinmays188/linkedin-mcp-server, a fork) WAS already confirmed working
(`git ls-remote` succeeded), so the real, live, undoable GitHub action
here is a git-level write instead: push a new branch with a trivial real
commit (the write), then delete that branch (the undo) -- both genuinely
live against a real remote, not mocked, not simulated.

This is a different, narrower capability than GitHubClient's REST reads
(commits/PRs/issues) -- kept as a separate class rather than bolted onto
GitHubClient, since the transport (git subprocess over SSH) and the
credential model (SSH key, not a Bearer token) are both genuinely
different, not just an implementation detail of the same client.
"""

import subprocess
import tempfile
import uuid
from pathlib import Path


class GitHubGitWriteError(Exception):
    pass


class GitHubGitWriteClient:
    def __init__(self, ssh_remote: str):
        self._ssh_remote = ssh_remote

    def push_branch_with_commit(self, branch_name: str, commit_message: str, file_content: str) -> str:
        """Real, live write: clones the real remote, creates a real new
        branch, writes a trivial real file, commits, and pushes it for
        real over SSH. Returns the real commit sha."""
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "repo"
            self._run(["git", "clone", "--depth", "1", self._ssh_remote, str(repo_dir)])
            self._run(["git", "checkout", "-b", branch_name], cwd=repo_dir)

            marker_file = repo_dir / f".hitl-undo-demo-{uuid.uuid4().hex[:8]}.txt"
            marker_file.write_text(file_content)

            self._run(["git", "add", marker_file.name], cwd=repo_dir)
            self._run(["git", "commit", "-m", commit_message], cwd=repo_dir)
            self._run(["git", "push", "origin", branch_name], cwd=repo_dir)

            sha = self._run(["git", "rev-parse", "HEAD"], cwd=repo_dir).strip()
            return sha

    def delete_branch(self, branch_name: str) -> None:
        """Real, live undo: deletes the real remote branch over SSH. Uses
        the full remote URL directly (not an "origin" shorthand) since
        there's no cloned working directory with that remote configured
        at this point -- this call doesn't need one."""
        self._run(["git", "push", self._ssh_remote, "--delete", branch_name])

    def _run(self, args: list[str], cwd: Path | None = None) -> str:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise GitHubGitWriteError(f"Command {args!r} failed: {result.stderr.strip()}")
        return result.stdout
