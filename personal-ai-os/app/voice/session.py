import time
import uuid

from pydantic import BaseModel, Field

from app.agents.base import AgentResponse
from app.agents.orchestrator import ClarificationNeeded, Orchestrator


class VoiceTurn(BaseModel):
    transcript: str
    response_text: str
    stt_latency_ms: float | None = None
    agent_latency_ms: float = 0.0
    total_latency_ms: float = 0.0


class VoiceSession:
    """Maintains conversation continuity across multiple voice turns for one
    session_id, and measures per-turn latency (Section 8: voice latency
    measurement is a required capability, not optional)."""

    def __init__(self, orchestrator: Orchestrator, session_id: str | None = None):
        self.session_id = session_id or uuid.uuid4().hex
        self._orchestrator = orchestrator
        self.turns: list[VoiceTurn] = []

    def handle_transcript(self, transcript: str, stt_latency_ms: float | None = None) -> VoiceTurn:
        if not transcript or not transcript.strip():
            raise ValueError("Transcript must not be empty.")

        start = time.monotonic()
        result = self._orchestrator.handle(transcript)
        agent_latency_ms = (time.monotonic() - start) * 1000

        response_text = (
            result.message if isinstance(result, ClarificationNeeded) else result.output
        )

        turn = VoiceTurn(
            transcript=transcript,
            response_text=response_text,
            stt_latency_ms=stt_latency_ms,
            agent_latency_ms=agent_latency_ms,
            total_latency_ms=agent_latency_ms + (stt_latency_ms or 0.0),
        )
        self.turns.append(turn)
        return turn


class VoiceSessionStore:
    """In-memory session registry, keyed by session_id, so a multi-turn voice
    conversation can continue across separate HTTP requests (browsers can't
    hold a persistent process-level object between calls)."""

    def __init__(self, orchestrator_factory):
        self._orchestrator_factory = orchestrator_factory
        self._sessions: dict[str, VoiceSession] = {}

    def get_or_create(self, session_id: str | None) -> VoiceSession:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]

        session = VoiceSession(self._orchestrator_factory(), session_id=session_id)
        self._sessions[session.session_id] = session
        return session
