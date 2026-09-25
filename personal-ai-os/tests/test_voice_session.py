import pytest

from app.agents.orchestrator import Orchestrator
from app.providers.base import LLMProvider
from app.voice.session import VoiceSession, VoiceSessionStore


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_handle_transcript_returns_agent_response_text():
    llm = ScriptedProvider(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "RAG combines retrieval with generation."}',
        ]
    )
    session = VoiceSession(Orchestrator(llm))

    turn = session.handle_transcript("Explain RAG.")

    assert turn.response_text == "RAG combines retrieval with generation."
    assert turn.transcript == "Explain RAG."


def test_handle_transcript_records_turn_in_history():
    llm = ScriptedProvider(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "answer"}',
        ]
    )
    session = VoiceSession(Orchestrator(llm))

    session.handle_transcript("Explain RAG.")

    assert len(session.turns) == 1


def test_handle_transcript_measures_latency():
    llm = ScriptedProvider(
        [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
            '{"action": "final_answer", "answer": "answer"}',
        ]
    )
    session = VoiceSession(Orchestrator(llm))

    turn = session.handle_transcript("Explain RAG.", stt_latency_ms=120.0)

    assert turn.stt_latency_ms == 120.0
    assert turn.agent_latency_ms >= 0
    assert turn.total_latency_ms >= turn.agent_latency_ms


def test_empty_transcript_raises():
    llm = ScriptedProvider([])
    session = VoiceSession(Orchestrator(llm))

    with pytest.raises(ValueError):
        session.handle_transcript("")


def test_ambiguous_transcript_returns_clarification_message():
    llm = ScriptedProvider(['{"domains": [], "confidence": 0.9}', '{"task_type": "unclear", "confidence": 0.9}'])
    session = VoiceSession(Orchestrator(llm))

    turn = session.handle_transcript("Do something useful.")

    assert "clarify" in turn.response_text.lower()


def test_session_store_creates_new_session_when_no_id_given():
    llm = ScriptedProvider([])
    store = VoiceSessionStore(orchestrator_factory=lambda: Orchestrator(llm))

    session = store.get_or_create(None)

    assert session.session_id


def test_session_store_reuses_existing_session_by_id():
    llm = ScriptedProvider([])
    store = VoiceSessionStore(orchestrator_factory=lambda: Orchestrator(llm))

    session1 = store.get_or_create(None)
    session2 = store.get_or_create(session1.session_id)

    assert session1 is session2


def test_session_store_creates_distinct_sessions_for_unknown_ids():
    llm = ScriptedProvider([])
    store = VoiceSessionStore(orchestrator_factory=lambda: Orchestrator(llm))

    session1 = store.get_or_create("does-not-exist-1")
    session2 = store.get_or_create("does-not-exist-2")

    assert session1.session_id != session2.session_id
