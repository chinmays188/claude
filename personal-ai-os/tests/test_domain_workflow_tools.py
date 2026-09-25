import json
from datetime import datetime, timezone

import pytest

from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.base import LLMProvider
from app.retrieval.document import Chunk
from app.retrieval.vector_search import VectorStore
from app.tools.base import ArgumentValidationError, ToolError
from app.tools.domain_workflow_tools import AnalyzeFeedbackTool, AnalyzeJdTool, DraftPrdTool
from tests.fakes.example_resume import EXAMPLE_ACHIEVEMENTS
from tests.fakes.fake_embedding import FakeEmbeddingModel

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _retriever_with_achievements() -> SecureRetriever:
    store = VectorStore(FakeEmbeddingModel())
    metadata = {}
    for achv_id, text in EXAMPLE_ACHIEVEMENTS:
        store.add([Chunk(id=f"{achv_id}::c0", document_id=achv_id, text=text, source="resume", created_at=NOW, updated_at=NOW, chunk_index=0)])
        metadata[achv_id] = PersonalDocumentMetadata(
            document_id=achv_id, source="resume", title="Achievements", created_at=NOW, updated_at=NOW,
            owner_id="alice", tenant_id="t1", sensitivity=Sensitivity.PERSONAL,
        )
    return SecureRetriever(store, metadata)


def test_analyze_feedback_tool_returns_json_result():
    llm = ScriptedProvider(
        ['{"top_themes": [], "emerging_themes": [], "declining_themes": [], '
         '"critical_issues": [], "recommended_actions": ["talk to more users"]}']
    )
    tool = AnalyzeFeedbackTool(llm)

    result = tool.call({"feedback_items": ["Refunds are slow.", "Support is unresponsive."]})

    data = json.loads(result)
    assert data["recommended_actions"] == ["talk to more users"]


def test_analyze_feedback_tool_rejects_empty_list():
    tool = AnalyzeFeedbackTool(ScriptedProvider([]))

    with pytest.raises(ToolError):
        tool.call({"feedback_items": []})


def test_analyze_feedback_tool_rejects_invalid_args():
    tool = AnalyzeFeedbackTool(ScriptedProvider([]))

    with pytest.raises(ArgumentValidationError):
        tool.call({"feedback_items": "not a list"})


def test_analyze_jd_tool_returns_json_result():
    llm = ScriptedProvider(
        [
            '{"role_title": "AI PM", "required_skills": ["AI"], "preferred_skills": [], '
            '"responsibilities": [], "seniority_signal": "senior"}',
            '{"overall_fit": 0.8, "technical_fit": 0.7, "ai_fit": 0.9, "pm_fit": 0.85, '
            '"domain_fit": 0.6, "leadership_fit": 0.75, "major_gaps": [], '
            '"recommended_resume_changes": [], "interview_risks": []}',
        ]
    )
    tool = AnalyzeJdTool(llm, _retriever_with_achievements(), requester_id="alice", requester_tenant_id="t1")

    result = tool.call({"jd_text": "Senior AI PM role."})

    data = json.loads(result)
    assert data["overall_fit"] == 0.8


def test_analyze_jd_tool_rejects_empty_jd_text():
    tool = AnalyzeJdTool(ScriptedProvider([]), _retriever_with_achievements(), requester_id="alice", requester_tenant_id="t1")

    with pytest.raises(ToolError):
        tool.call({"jd_text": ""})


def test_draft_prd_tool_returns_json_result():
    llm = ScriptedProvider(
        ['{"problem_statement": "Refunds are slow.", "customer_context": "post-sales users", '
         '"hypothesis": "automation reduces resolution time", "solution": "self-serve refund flow", '
         '"metrics": ["resolution time"], "experiment": "A/B test on 10% of traffic"}']
    )
    tool = DraftPrdTool(llm, _retriever_with_achievements(), requester_id="alice", requester_tenant_id="t1")

    result = tool.call({"idea": "Self-serve refund automation."})

    data = json.loads(result)
    assert data["solution"] == "self-serve refund flow"


def test_draft_prd_tool_rejects_empty_idea():
    tool = DraftPrdTool(ScriptedProvider([]), _retriever_with_achievements(), requester_id="alice", requester_tenant_id="t1")

    with pytest.raises(ToolError):
        tool.call({"idea": ""})
