from app.integrations.github_client import GitHubActivity


def summarize_activity(activity: GitHubActivity) -> str:
    """Turns raw commits/PRs/issues into a text summary an LLM can ground an
    answer in — deliberately NOT an LLM call itself, so the summary is a
    faithful, deterministic listing of what actually happened (Section 23:
    'no fabricated activity'). The LLM's job is to phrase this nicely, not to
    invent what was in it."""
    lines = [f"Activity in {activity.repo} from {activity.since.date()} to {activity.until.date()}:"]

    if activity.commits:
        lines.append(f"\nCommits ({len(activity.commits)}):")
        for c in activity.commits:
            lines.append(f"- {c.committed_at.date()} [{c.sha[:7]}] {c.message.splitlines()[0]}")

    if activity.pull_requests:
        lines.append(f"\nPull requests ({len(activity.pull_requests)}):")
        for pr in activity.pull_requests:
            status = "merged" if pr.merged_at else pr.state
            lines.append(f"- #{pr.number} {pr.title} ({status})")

    if activity.issues:
        lines.append(f"\nIssues ({len(activity.issues)}):")
        for issue in activity.issues:
            lines.append(f"- #{issue.number} {issue.title} ({issue.state})")

    if not (activity.commits or activity.pull_requests or activity.issues):
        lines.append("\nNo activity recorded in this period.")

    return "\n".join(lines)
