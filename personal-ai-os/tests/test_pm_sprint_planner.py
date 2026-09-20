from app.domains.pm.sprint_planner import create_sprint_plan
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_create_sprint_plan_prioritizes_across_sources():
    llm = ScriptedProvider(
        ['{"prioritized_work": [{"title": "Fix refund bug", "source": "bug", "priority": 0.9, "owner": "alice", "dependencies": [], "risk": "low"}], '
         '"risks": ["tight timeline"], "suggested_sprint_scope": ["Fix refund bug"]}']
    )

    plan = create_sprint_plan(
        llm,
        stakeholder_requests=["Add automated refunds"],
        backlog=["Improve onboarding flow"],
        bugs=["Refund calculation bug"],
        commitments=["Ship X by Friday"],
    )

    assert plan.prioritized_work[0].title == "Fix refund bug"
    assert plan.prioritized_work[0].source == "bug"
    assert "Fix refund bug" in plan.suggested_sprint_scope


def test_create_sprint_plan_handles_all_empty_sources():
    llm = ScriptedProvider(['{"prioritized_work": [], "risks": [], "suggested_sprint_scope": []}'])

    plan = create_sprint_plan(llm, stakeholder_requests=[], backlog=[], bugs=[], commitments=[])

    assert plan.prioritized_work == []


def test_sprint_planner_has_no_write_methods():
    # Structural guarantee, mirroring Calendar/Email clients (Phase 2, M24):
    # Section 18 requires the sprint planner never auto-write to Jira/PM tools.
    import app.domains.pm.sprint_planner as module

    assert not hasattr(module, "create_jira_item")
    assert not hasattr(module, "update_jira")
