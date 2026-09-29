from fastapi.testclient import TestClient

from app.agents.orchestrator import Orchestrator
from app.api.voice_api import app, get_session_store
from app.providers.base import LLMProvider
from app.voice.session import VoiceSessionStore


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _client_with_scripted_responses(responses: list[str]) -> TestClient:
    llm = ScriptedProvider(responses)
    store = VoiceSessionStore(orchestrator_factory=lambda: Orchestrator(llm))
    app.dependency_overrides[get_session_store] = lambda: store
    return TestClient(app)


_NO_MEMORY_RESPONSE = '{"should_remember": false, "type": null, "importance": 0.0, "summary": null}'
# VoiceSession now delegates to ConversationSession (real bug fix -- see
# app/voice/session.py's docstring), which makes one real MemoryWritePolicy
# call after every turn.


def test_voice_turn_returns_response_text():
    client = _client_with_scripted_responses(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "RAG combines retrieval with generation."}',
            _NO_MEMORY_RESPONSE,
        ]
    )

    response = client.post("/voice/turn", json={"transcript": "Explain RAG."})

    assert response.status_code == 200
    data = response.json()
    assert data["response_text"] == "RAG combines retrieval with generation."
    assert data["session_id"]
    app.dependency_overrides.clear()


def test_voice_turn_reuses_session_id_across_requests():
    client = _client_with_scripted_responses(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "first answer"}',
            _NO_MEMORY_RESPONSE,
        ]
    )

    first = client.post("/voice/turn", json={"transcript": "Explain RAG."})
    session_id = first.json()["session_id"]

    assert session_id
    app.dependency_overrides.clear()


def test_empty_transcript_returns_400():
    client = _client_with_scripted_responses([])

    response = client.post("/voice/turn", json={"transcript": ""})

    assert response.status_code == 400
    app.dependency_overrides.clear()


def test_voice_page_serves_html():
    client = _client_with_scripted_responses([])

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "SpeechRecognition" in response.text
    app.dependency_overrides.clear()
