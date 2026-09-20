from pydantic import BaseModel, Field

from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

WEEKLY_REVIEW_PROMPT = """Produce a weekly review using ONLY the source data
below. Do not invent accomplishments, decisions, or events not present in the
sources (Section 38's fabrication rules apply across all domains here).

Calendar: {calendar}
GitHub activity: {github}
Tasks: {tasks}
Projects: {projects}
Learning progress: {learning}
Career activity: {career}
Goals: {goals}
Finance: {finance}
Commitments: {commitments}

Respond with ONLY a JSON object matching Section 35's exact structure:
{{
  "what_happened": "<summary grounded in the sources above>",
  "accomplishments": ["<grounded accomplishment>"],
  "changes": ["<what changed since last week>"],
  "behind": ["<what is behind schedule>"],
  "requires_attention": ["<something requiring attention>"],
  "decisions_made": ["<a decision, grounded in the sources>"],
  "next_week": ["<recommended focus for next week>"]
}}
"""


class WeeklyReview(BaseModel):
    """Section 35's exact structure."""

    what_happened: str
    accomplishments: list[str] = Field(default_factory=list)
    changes: list[str] = Field(default_factory=list)
    behind: list[str] = Field(default_factory=list)
    requires_attention: list[str] = Field(default_factory=list)
    decisions_made: list[str] = Field(default_factory=list)
    next_week: list[str] = Field(default_factory=list)


class WeeklyReviewSources(BaseModel):
    """Section 35's exact input list — pre-collected by the caller from each
    domain/integration, so this module stays decoupled from GitHub/Calendar/
    Memory/etc. and is fully testable with plain strings."""

    calendar: str = "(no calendar data)"
    github: str = "(no GitHub activity)"
    tasks: str = "(no task data)"
    projects: str = "(no project data)"
    learning: str = "(no learning progress)"
    career: str = "(no career activity)"
    goals: str = "(no goal data)"
    finance: str = "(no finance data)"
    commitments: str = "(no commitments)"


def generate_weekly_review(llm: LLMProvider, sources: WeeklyReviewSources) -> WeeklyReview:
    generator = RepairableGenerator(llm, WeeklyReview)
    prompt = WEEKLY_REVIEW_PROMPT.format(
        calendar=sources.calendar, github=sources.github, tasks=sources.tasks, projects=sources.projects,
        learning=sources.learning, career=sources.career, goals=sources.goals, finance=sources.finance,
        commitments=sources.commitments,
    )
    return generator.generate(prompt)
