import sqlite3
import time
import uuid

from pydantic import BaseModel

from app.agents.orchestrator import Orchestrator
from app.conversation.session import ConversationSession
from app.memory.persistent_store import PersistentMemoryStore
from app.memory.retrieval import MemoryRetriever
from app.memory.write_policy import MemoryWritePolicy
from app.retrieval.embeddings import EmbeddingModel

DEFAULT_TENANT_ID = "voice_tenant"
DEFAULT_USER_ID = "voice_user"


class VoiceTurn(BaseModel):
    transcript: str
    response_text: str
    stt_latency_ms: float | None = None
    agent_latency_ms: float = 0.0
    total_latency_ms: float = 0.0


class VoiceSession:
    """Maintains conversation continuity across multiple voice turns for one
    session_id, and measures per-turn latency (Section 8: voice latency
    measurement is a required capability, not optional).

    Real bug fixed here (found while breaking down this project's context
    engineering): self.turns was appended to on every call but NEVER
    actually passed back into Orchestrator.handle() -- "conversation
    continuity across multiple voice turns" was claimed in this class's own
    docstring but wasn't real; every turn was independently stateless.
    Fixed by delegating to the new app/conversation/session.py's
    ConversationSession, which actually injects prior-turn context (and
    real semantic memory) into each request. tenant_id/user_id/memory
    dependencies are optional and default to fresh, in-memory-SQLite,
    per-voice-session values so every existing caller (this class's own
    constructor signature is unchanged) keeps working with zero code
    changes -- they just now get the real fix for free."""

    def __init__(
        self,
        orchestrator: Orchestrator,
        session_id: str | None = None,
        conversation_session: ConversationSession | None = None,
    ):
        self.session_id = session_id or uuid.uuid4().hex
        self._orchestrator = orchestrator
        self.turns: list[VoiceTurn] = []
        self._conversation = conversation_session or _default_conversation_session(orchestrator, self.session_id)

    def handle_transcript(self, transcript: str, stt_latency_ms: float | None = None) -> VoiceTurn:
        if not transcript or not transcript.strip():
            raise ValueError("Transcript must not be empty.")

        start = time.monotonic()
        response_text = self._conversation.handle(transcript)
        agent_latency_ms = (time.monotonic() - start) * 1000

        turn = VoiceTurn(
            transcript=transcript,
            response_text=response_text,
            stt_latency_ms=stt_latency_ms,
            agent_latency_ms=agent_latency_ms,
            total_latency_ms=agent_latency_ms + (stt_latency_ms or 0.0),
        )
        self.turns.append(turn)
        return turn


class _WordCountEmbedding(EmbeddingModel):
    """A default, dependency-free embedding for VoiceSession's own
    MemoryRetriever when the caller doesn't supply a real one --
    deliberately weak (same honesty standard as naive_relevance.py: no
    fabricated semantic understanding), just enough to not crash when no
    memories exist yet, which is the common case for a fresh voice session."""

    def embed(self, texts: list[str]):
        import numpy as np

        return np.asarray([[float(len(t.split()))] for t in texts], dtype="float32")

    @property
    def dimension(self) -> int:
        return 1


def _default_conversation_session(orchestrator: Orchestrator, session_id: str) -> ConversationSession:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    memory_store = PersistentMemoryStore(conn)
    memory_retriever = MemoryRetriever(_WordCountEmbedding())
    write_policy = MemoryWritePolicy(orchestrator.llm)
    return ConversationSession(
        orchestrator, orchestrator.llm, memory_store, memory_retriever, write_policy,
        tenant_id=DEFAULT_TENANT_ID, user_id=DEFAULT_USER_ID, session_id=session_id,
    )


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
