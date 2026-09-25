"""Generates a real request/response example for every registered tool, by
actually invoking each one (never hand-written/fabricated examples), and
writes app/dashboard_ui/tool_examples.json for the dashboard's Tools page.

Answers the user's question: "how to add more tools (when can each of these
tools be called need to be on UI with their request and response example)."

For tools needing external credentials (calendar/email/github), the
"external client" is the same in-memory/mocked fixture pattern this
codebase's own tests already use (CalendarClient's caller-supplied list,
GitHubClient's mocked HTTP transport) -- real code execution against
synthetic, clearly-labeled fixture data, not fabricated example text.
email_summary additionally needs a real Gemini call (it classifies each
email via the LLM) -- this script requires GEMINI_API_KEY for that one tool
only; every other tool needs no API key.

Usage:
    PYTHONPATH=. python scripts/generate_tool_examples.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.config import require_gemini_key
from app.integrations.calendar_client import CalendarClient, CalendarEvent
from app.integrations.email_client import Email, EmailClient
from app.integrations.github_client import GitHubClient
from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.knowledge.secure_retrieval import SecureRetriever
from app.providers.gemini_provider import GeminiProvider
from app.retrieval.document import Chunk
from app.retrieval.vector_search import VectorStore
from app.tools.base import Tool
from app.tools.calculator import CalculatorTool
from app.tools.calendar_tool import CalendarDayTool
from app.tools.domain_workflow_tools import AnalyzeFeedbackTool, AnalyzeJdTool, DraftPrdTool
from app.tools.email_tool import EmailSummaryTool
from app.tools.github_tool import GitHubActivityTool
from app.tools.retrieval_tool import RetrievalTool

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "tool_examples.json"

NOW = datetime(2026, 1, 15, tzinfo=timezone.utc)


class FakeEmbeddingModel:
    """Deterministic, no-network embedding for this generator's own small
    fixture document -- same approach as tests/fakes/fake_embedding.py, kept
    local here so this script has zero dependency on the tests/ package."""

    def __init__(self, dimension: int = 16):
        self._dimension = dimension

    def embed(self, texts):
        import hashlib

        import numpy as np

        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            vectors.append([digest[i % len(digest)] / 255.0 for i in range(self._dimension)])
        return np.asarray(vectors, dtype="float32")

    @property
    def dimension(self) -> int:
        return self._dimension


def _example(tool: Tool, request_args: dict, response: str, when_to_call: str) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "permissions": tool.permissions,
        "args_schema": tool.args_schema.model_json_schema(),
        "when_to_call": when_to_call,
        "example_request": request_args,
        "example_response": response,
    }


def build_examples() -> list[dict]:
    examples = []

    # calculator -- no dependency
    calc = CalculatorTool()
    req = {"expression": "47 * 12"}
    examples.append(_example(
        calc, req, calc.call(req),
        "Any request needing real arithmetic (comparisons, timelines, budgets) -- "
        "never let the LLM guess a calculation.",
    ))

    # retrieve -- real FAISS + fake (fast, no-network) embeddings over one small fixture document
    store = VectorStore(FakeEmbeddingModel())
    store.add([Chunk(
        id="fixture_doc::c0", document_id="fixture_doc",
        text="Kubernetes is a container orchestration platform for automating deployment and scaling.",
        source="fixture", created_at=NOW, updated_at=NOW, chunk_index=0,
    )])
    retrieve = RetrievalTool(store)
    req = {"query": "container orchestration", "top_k": 3}
    examples.append(_example(
        retrieve, req, retrieve.call(req),
        "When the user's question might be answered by something already indexed "
        "(via --index-file) -- grounds the answer instead of guessing.",
    ))

    # calendar_day -- real CalendarClient, caller-supplied fixture events
    calendar_client = CalendarClient([
        CalendarEvent(event_id="e1", title="Sprint planning", start=NOW.replace(hour=9), end=NOW.replace(hour=10)),
        CalendarEvent(event_id="e2", title="1:1 with manager", start=NOW.replace(hour=9, minute=30), end=NOW.replace(hour=10)),
    ])
    calendar_tool = CalendarDayTool(calendar_client)
    req = {"day": NOW.isoformat()}
    examples.append(_example(
        calendar_tool, req, calendar_tool.call(req),
        "Questions like 'what's on my calendar today' or 'do I have any scheduling "
        "conflicts' -- needs a real CalendarClient (OAuth-authenticated in production, "
        "not wired into this trace CLI).",
    ))

    # github_activity -- real GitHubClient, mocked HTTP transport (same as tests/test_github_tool.py)
    def handler(request: httpx.Request) -> httpx.Response:
        if "/commits" in str(request.url):
            return httpx.Response(200, json=[{
                "sha": "abc1234def", "commit": {"message": "Fix refund calculation bug", "author": {"name": "alice", "date": "2026-01-10T00:00:00Z"}},
            }])
        return httpx.Response(200, json=[])

    http_client = httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(handler))
    github_client = GitHubClient(token="fixture-token", http_client=http_client)
    github_tool = GitHubActivityTool(github_client)
    req = {"repo": "owner/repo", "since": "2026-01-01T00:00:00Z", "until": "2026-01-31T00:00:00Z"}
    examples.append(_example(
        github_tool, req, github_tool.call(req),
        "Questions like 'what did I accomplish on this project this week' -- needs a "
        "real GitHubClient with a real API token (not wired into this trace CLI).",
    ))

    # email_summary -- real EmailClient + a real Gemini call for classification
    require_gemini_key()
    llm = GeminiProvider()
    email_client = EmailClient([
        Email(email_id="em1", sender="boss@company.com", subject="Q3 roadmap review", body="Please review the attached roadmap by Friday.", received_at=NOW),
    ])
    email_tool = EmailSummaryTool(email_client, llm)
    req = {"since": "2026-01-01T00:00:00Z", "until": "2026-01-31T00:00:00Z"}
    examples.append(_example(
        email_tool, req, email_tool.call(req),
        "Questions like 'what important emails did I get today' -- needs a real "
        "EmailClient (not wired into this trace CLI) and makes a real Gemini call "
        "per email to classify it.",
    ))

    # analyze_feedback -- no dependency beyond the LLM
    feedback_tool = AnalyzeFeedbackTool(llm)
    req = {"feedback_items": ["Refunds take too long.", "Support never responds."]}
    examples.append(_example(
        feedback_tool, req, feedback_tool.call(req),
        "The user gives you multiple pieces of raw feedback to make sense of -- "
        "clusters into themes, estimates severity, recommends actions.",
    ))

    # analyze_jd / draft_prd -- need a SecureRetriever over the user's own documents
    metadata = {
        "fixture_doc": PersonalDocumentMetadata(
            document_id="fixture_doc", source="resume", title="Fixture achievements",
            created_at=NOW, updated_at=NOW, category="career",
            sensitivity=Sensitivity.PERSONAL, owner_id="fixture_user", tenant_id="fixture_tenant",
        )
    }
    achievement_store = VectorStore(FakeEmbeddingModel())
    achievement_store.add([Chunk(
        id="fixture_doc::c0", document_id="fixture_doc",
        text="Led a cross-functional team of 6 to launch a self-serve refund flow, "
             "reducing average refund resolution time from 5 days to 8 hours.",
        source="resume", created_at=NOW, updated_at=NOW, chunk_index=0,
    )])
    secure_retriever = SecureRetriever(achievement_store, metadata)

    jd_tool = AnalyzeJdTool(llm, secure_retriever, requester_id="fixture_user", requester_tenant_id="fixture_tenant")
    req = {"jd_text": "Senior Product Manager, requires 3+ years PM experience and cross-functional leadership."}
    examples.append(_example(
        jd_tool, req, jd_tool.call(req),
        "The user pastes a job description and asks about fit -- requires documents "
        "already indexed (e.g. via --index-file); returns an error otherwise.",
    ))

    prd_tool = DraftPrdTool(llm, secure_retriever, requester_id="fixture_user", requester_tenant_id="fixture_tenant")
    req = {"idea": "Automate refund status notifications for customers."}
    examples.append(_example(
        prd_tool, req, prd_tool.call(req),
        "The user describes a product idea and asks for a PRD -- requires documents "
        "already indexed to ground context; works without grounding if none indexed.",
    ))

    return examples


def main() -> None:
    examples = build_examples()
    OUTPUT_PATH.write_text(json.dumps(examples, indent=2, default=str))
    print(f"Wrote {len(examples)} real tool examples to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
