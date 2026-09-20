from app.domains.cross_domain.daily_brief import DailyBrief, DailyBriefSources, generate_daily_brief
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_generate_daily_brief_returns_priorities():
    llm = ScriptedProvider(['{"priorities": ["Follow up with stakeholder X", "Review PR #12"]}'])

    brief = generate_daily_brief(llm, DailyBriefSources(commitments="Reply to stakeholder X by EOD."))

    assert brief.priorities[0] == "Follow up with stakeholder X"


def test_daily_brief_has_no_execution_fields():
    # Section 36: advisory only, until Phase 4 -- structurally, there is
    # nothing on this model resembling an approval/execution flag.
    fields = DailyBrief.model_fields.keys()

    assert "approved" not in fields
    assert "executed" not in fields
