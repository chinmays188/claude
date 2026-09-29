import sqlite3

from app.agents.orchestrator import Orchestrator
from app.conversation.session import ConversationSession
from app.memory.persistent_store import PersistentMemoryStore
from app.memory.retrieval import MemoryRetriever
from app.memory.write_policy import MemoryWritePolicy
from app.providers.base import LLMProvider
from tests.fakes.fake_embedding import FakeEmbeddingModel

TENANT_ID = "t1"
USER_ID = "u1"


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _make_session(responses: list[str], **kwargs) -> ConversationSession:
    llm = ScriptedProvider(responses)
    orchestrator = Orchestrator(llm)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    memory_store = PersistentMemoryStore(conn)
    memory_retriever = MemoryRetriever(FakeEmbeddingModel())
    write_policy = MemoryWritePolicy(llm)
    return ConversationSession(
        orchestrator, llm, memory_store, memory_retriever, write_policy,
        tenant_id=TENANT_ID, user_id=USER_ID, **kwargs,
    )


def _orchestrator_turn_responses(answer: str) -> list[str]:
    """One Orchestrator.handle() call's real response sequence for a
    simple, non-multi-agent input: 2 classification calls + 1 agent
    decision call."""
    return [
        '{"domains": [], "confidence": 0.9}',
        '{"task_type": "research", "confidence": 0.9}',
        f'{{"action": "final_answer", "answer": "{answer}"}}',
    ]


def _write_policy_no_memory() -> str:
    return '{"should_remember": false, "type": null, "importance": 0.0, "summary": null}'


def _single_mode_plan_response() -> str:
    """Injected memory/history context can push the prompted text over
    might_need_multiple_agents()'s free word-count heuristic, adding one
    real MultiAgentPlanner call before routing even happens -- a real,
    worth-knowing interaction this test surfaces, not an artifact to hide."""
    return '{"agents": [], "mode": "SINGLE", "reasoning": "A single agent can handle this."}'


def test_first_turn_has_no_prior_context_injected():
    responses = _orchestrator_turn_responses("Hello there.") + [_write_policy_no_memory()]
    session = _make_session(responses)

    response = session.handle("Hi.")

    assert response == "Hello there."
    assert len(session.turns) == 1


def test_second_turn_gets_prior_turn_injected_into_the_prompt():
    seen_prompts = []

    class RecordingProvider(ScriptedProvider):
        def generate(self, prompt: str) -> str:
            seen_prompts.append(prompt)
            return super().generate(prompt)

    responses = (
        _orchestrator_turn_responses("First answer.") + [_write_policy_no_memory()]
        + _orchestrator_turn_responses("Second answer.") + [_write_policy_no_memory()]
    )
    llm = RecordingProvider(responses)
    orchestrator = Orchestrator(llm)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    session = ConversationSession(
        orchestrator, llm, PersistentMemoryStore(conn), MemoryRetriever(FakeEmbeddingModel()),
        MemoryWritePolicy(llm), tenant_id=TENANT_ID, user_id=USER_ID,
    )

    session.handle("What is RAG?")
    session.handle("Can you say more?")

    # The 4th real LLM call in this run is the second turn's agent decision
    # call -- its prompt must contain the first turn's real content.
    second_turn_agent_prompt = seen_prompts[3]
    assert "What is RAG?" in second_turn_agent_prompt
    assert "First answer." in second_turn_agent_prompt


def test_history_compresses_via_real_summary_call_once_over_budget():
    responses = (
        _orchestrator_turn_responses("Answer one, quite a long one to burn through the token budget quickly on purpose.")
        + [_write_policy_no_memory()]
        + [_single_mode_plan_response()]  # 2nd turn's injected prior-turn context trips the heuristic
        + _orchestrator_turn_responses("Answer two, also fairly long to keep pushing past the small test budget.")
        # Compression runs BEFORE the write-policy call in ConversationSession.handle():
        + ['{"summary": "User asked two questions; assistant answered both."}']
        + [_write_policy_no_memory()]
        + [_single_mode_plan_response()]  # 3rd turn also carries injected context
        + _orchestrator_turn_responses("Answer three.")
        # Still over the tiny test budget after turn 3 -- compression fires again.
        + ['{"summary": "User asked three questions; assistant answered all of them."}']
        + [_write_policy_no_memory()]
    )
    session = _make_session(responses, history_token_budget=5, recent_turns_kept_verbatim=1)

    session.handle("Question one?")
    session.handle("Question two?")
    assert session.running_summary  # compression triggered for real
    session.handle("Question three?")

    assert "User asked three questions" in session.running_summary  # compressed again, real 2nd summary call


def test_memory_write_policy_gate_writes_low_importance_directly():
    responses = _orchestrator_turn_responses("Noted.") + [
        '{"should_remember": true, "type": "preference", "importance": 0.4, "summary": "Prefers concise answers."}'
    ]
    session = _make_session(responses)

    session.handle("I prefer concise answers.")

    memories = session._memory_store.list_all(TENANT_ID, USER_ID)
    assert len(memories) == 1
    assert memories[0].content == "Prefers concise answers."
    assert session.pending_memory_approvals == []


def test_memory_write_policy_gate_queues_high_importance_for_approval():
    responses = _orchestrator_turn_responses("Got it.") + [
        '{"should_remember": true, "type": "goal", "importance": 0.9, "summary": "Wants to become a senior PM."}'
    ]
    session = _make_session(responses)

    session.handle("My goal is to become a senior PM.")

    assert session._memory_store.list_all(TENANT_ID, USER_ID) == []  # not auto-written
    assert len(session.pending_memory_approvals) == 1
    assert session.pending_memory_approvals[0].summary == "Wants to become a senior PM."


def test_approve_pending_memory_writes_it():
    responses = _orchestrator_turn_responses("Got it.") + [
        '{"should_remember": true, "type": "goal", "importance": 0.9, "summary": "Wants to become a senior PM."}'
    ]
    session = _make_session(responses)
    session.handle("My goal is to become a senior PM.")
    turn_id = session.pending_memory_approvals[0].turn_id

    record = session.approve_pending_memory(turn_id)

    assert record is not None
    memories = session._memory_store.list_all(TENANT_ID, USER_ID)
    assert len(memories) == 1
    assert session.pending_memory_approvals == []


def test_approve_pending_memory_returns_none_for_unknown_turn_id():
    responses = _orchestrator_turn_responses("Hi.") + [_write_policy_no_memory()]
    session = _make_session(responses)
    session.handle("Hi.")

    assert session.approve_pending_memory("no-such-id") is None


def test_relevant_stored_memory_is_injected_into_the_prompt():
    seen_prompts = []

    class RecordingProvider(ScriptedProvider):
        def generate(self, prompt: str) -> str:
            seen_prompts.append(prompt)
            return super().generate(prompt)

    responses = [_single_mode_plan_response()] + _orchestrator_turn_responses("Here you go.") + [_write_policy_no_memory()]
    llm = RecordingProvider(responses)
    orchestrator = Orchestrator(llm)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    memory_store = PersistentMemoryStore(conn)

    from datetime import datetime, timezone
    from app.memory.models import MemoryRecord, MemoryType

    now = datetime.now(timezone.utc)
    memory_store.write(
        MemoryRecord(
            memory_id="m1", tenant_id=TENANT_ID, user_id=USER_ID, type=MemoryType.PREFERENCE,
            content="Prefers bullet points over paragraphs.", source="test",
            created_at=now, updated_at=now, importance=0.8, user_confirmed=True,
        )
    )

    session = ConversationSession(
        orchestrator, llm, memory_store, MemoryRetriever(FakeEmbeddingModel()),
        MemoryWritePolicy(llm), tenant_id=TENANT_ID, user_id=USER_ID,
    )
    session.handle("Explain RAG to me.")

    agent_decision_prompt = seen_prompts[-2]  # last is the write-policy call, which runs after
    assert "Prefers bullet points over paragraphs." in agent_decision_prompt
