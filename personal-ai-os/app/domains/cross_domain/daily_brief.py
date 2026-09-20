from pydantic import BaseModel, Field

from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

DAILY_BRIEF_PROMPT = """Produce today's priorities using ONLY the source data
below. This is ADVISORY ONLY (Section 36) — you are suggesting priorities for
the user to consider, never committing to or executing anything. Do not
invent commitments or calendar events not present in the sources.

Today's calendar: {calendar}
Pending commitments: {commitments}
Project blockers: {blockers}
Career tasks: {career_tasks}
Learning goal: {learning_goal}
Important personal tasks: {personal_tasks}

Respond with ONLY a JSON object:
{{"priorities": ["<a specific, actionable priority for today, in suggested order>"]}}
"""


class DailyBrief(BaseModel):
    """Section 36's exact output — a plain ordered list of priorities.
    Advisory only: this model has no 'approved'/'executed' field at all,
    because Section 36 is explicit that this capability 'should remain
    advisory until Phase 4' — there is nothing here for a caller to
    accidentally treat as an authorization to act."""

    priorities: list[str] = Field(default_factory=list)


class DailyBriefSources(BaseModel):
    calendar: str = "(no calendar data)"
    commitments: str = "(no pending commitments)"
    blockers: str = "(no known blockers)"
    career_tasks: str = "(no career tasks)"
    learning_goal: str = "(no active learning goal)"
    personal_tasks: str = "(no personal tasks)"


def generate_daily_brief(llm: LLMProvider, sources: DailyBriefSources) -> DailyBrief:
    generator = RepairableGenerator(llm, DailyBrief)
    prompt = DAILY_BRIEF_PROMPT.format(
        calendar=sources.calendar, commitments=sources.commitments, blockers=sources.blockers,
        career_tasks=sources.career_tasks, learning_goal=sources.learning_goal, personal_tasks=sources.personal_tasks,
    )
    return generator.generate(prompt)
