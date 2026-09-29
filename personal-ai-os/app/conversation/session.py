"""Real, stateful conversation session -- closes the two real gaps found
while breaking down this project's context engineering, per the user's
ask: "let us first breakdown session memory, user memory, long term
memory ... after how many turn are we summarizing the session ... concept
of context window/compression ... how is ordering of memory happening."

What was found, checked directly against the code (not assumed):
  1. Orchestrator.handle(text) is completely stateless -- one string in,
     one answer out, no history parameter at all. VoiceSession recorded
     every VoiceTurn into self.turns but never actually passed them back
     into Orchestrator.handle() -- "conversation continuity across
     multiple voice turns" was claimed in a docstring but not real.
  2. Three separate memory subsystems existed, disconnected: the real
     semantic MemoryRetriever (similarity/recency/importance/confirmed)
     and the real MemoryWritePolicy (classify -> importance threshold ->
     duplicate check -> approval gate) were both fully built and tested,
     but never called from any live request path -- only
     naive_relevance.py (explicitly keyword-overlap-only, NOT semantic)
     was actually wired into scripts/trace_request.py/Orchestrator.

This module is the fix: a real ConversationSession that
  - keeps real per-turn history (not reconstructed after the fact),
  - injects recent turns as real context into the next request (closing
    gap 1, without changing Orchestrator.handle()'s signature -- every
    existing stateless caller is unaffected),
  - triggers a real, one-LLM-call summary of older turns once the
    estimated token cost of history exceeds a budget (context/builder.py's
    existing estimate_tokens() word-count proxy, reused rather than a new
    one invented) -- a token-budget trigger, not an arbitrary turn count,
    since that's what actually determines whether history fits the prompt,
  - reads memory via the real MemoryRetriever instead of
    naive_relevance.py (closing gap 2's read side),
  - writes memory via the real MemoryWritePolicy after each turn,
    respecting its real approval-required gate for high-importance
    candidates (closing gap 2's write side) -- nothing auto-writes a
    high-importance memory without going through that gate, matching this
    project's standing human-in-the-loop principle.
"""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.agents.orchestrator import ClarificationNeeded, Orchestrator
from app.context.builder import estimate_tokens
from app.context.personal_context_engine import PersonalContextEngine
from app.conversation.context_selection import select_context_text
from app.memory.models import MemoryRecord, MemoryType
from app.memory.persistent_store import PersistentMemoryStore
from app.memory.retrieval import MemoryRetriever
from app.memory.write_policy import MemoryWritePolicy
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

SUMMARY_PROMPT = """Summarize the following older conversation turns into a
short, factual running summary that preserves anything a later turn might
need to refer back to (stated preferences, decisions, facts, unresolved
questions). Do not invent anything not present in the turns below.

Older turns:
{turns_text}

Respond with ONLY a JSON object:
{{"summary": "<the running summary>"}}
"""


class _RunningSummary(BaseModel):
    summary: str


class ConversationTurn(BaseModel):
    turn_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    user_text: str
    response_text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PendingMemoryApproval(BaseModel):
    """Mirrors app/actions/policy_engine.py's ApprovalPending pattern: a
    high-importance memory candidate is surfaced, not silently written,
    when MemoryWritePolicy's approval_threshold is met."""

    turn_id: str
    summary: str
    memory_type: MemoryType | None
    importance: float


class ConversationSession:
    """One real, stateful session over Orchestrator. Deliberately does not
    change Orchestrator.handle()'s signature -- every existing stateless
    caller (scripts/trace_request.py, tests) is unaffected; this wraps it."""

    def __init__(
        self,
        orchestrator: Orchestrator,
        llm: LLMProvider,
        memory_store: PersistentMemoryStore,
        memory_retriever: MemoryRetriever,
        write_policy: MemoryWritePolicy,
        tenant_id: str,
        user_id: str,
        session_id: str | None = None,
        history_token_budget: int = 800,
        recent_turns_kept_verbatim: int = 2,
        context_engine: PersonalContextEngine | None = None,
        context_token_budget: int = 400,
    ):
        self.session_id = session_id or uuid.uuid4().hex
        self._orchestrator = orchestrator
        self._llm = llm
        self._memory_store = memory_store
        self._memory_retriever = memory_retriever
        self._write_policy = write_policy
        self._tenant_id = tenant_id
        self._user_id = user_id
        self._history_token_budget = history_token_budget
        self._recent_turns_kept_verbatim = recent_turns_kept_verbatim
        # Real PersonalContextEngine wiring (previously never called from
        # anywhere): selects which of {running summary, recent turns,
        # ranked memories} actually earns a place in the prompt, by real
        # relevance/importance/freshness/confidence score, under a real
        # token budget -- separate from history_token_budget, which only
        # governs when to SUMMARIZE, not what's selected into the prompt.
        self._context_engine = context_engine or PersonalContextEngine()
        self._context_token_budget = context_token_budget

        self.turns: list[ConversationTurn] = []
        self.running_summary: str = ""
        self.pending_memory_approvals: list[PendingMemoryApproval] = []
        # Populated by _build_prompted_text() every call -- lets a caller
        # (e.g. the dashboard's live Context Engineering page) inspect
        # exactly what was selected vs excluded and why, not just the
        # final rendered text.
        self.last_selected_context: list = []
        self.last_excluded_context: list = []

    def handle(self, user_text: str) -> str:
        if not user_text or not user_text.strip():
            raise ValueError("user_text must not be empty.")

        prompted_text = self._build_prompted_text(user_text)

        result = self._orchestrator.handle(prompted_text)
        response_text = result.message if isinstance(result, ClarificationNeeded) else result.output

        turn = ConversationTurn(user_text=user_text, response_text=response_text)
        self.turns.append(turn)
        self._compress_history_if_needed()
        self._maybe_write_memory(turn)

        return response_text

    def _build_prompted_text(self, user_text: str) -> str:
        """Closes gap 1: real prior-turn context + real semantic-memory
        context, injected as plain text ahead of the new request --
        Orchestrator.handle() still just sees one string, so every internal
        routing/tool-calling path behaves exactly as it already does and is
        already tested to.

        Real selection, not just concatenation (the "minimum useful
        context, not the maximum" principle, made demonstrable): every
        candidate (summary, recent turns, ranked memories) is scored by the
        real PersonalContextEngine and only included if it earns its place
        under context_token_budget -- a low-relevance memory or an old
        turn can now genuinely be excluded, inspectable afterward via
        self.last_excluded_context."""
        recent = self.turns[-self._recent_turns_kept_verbatim:] if self.turns else []

        candidates = self._memory_store.list_all(self._tenant_id, self._user_id)
        ranked_memories = self._memory_retriever.rank(user_text, candidates, top_k=5) if candidates else []

        context_text, selected, excluded = select_context_text(
            self._context_engine, self.running_summary, recent, ranked_memories,
            token_budget=self._context_token_budget,
        )
        self.last_selected_context = selected
        self.last_excluded_context = excluded

        if not context_text:
            return user_text

        return f"{context_text}\n\nCurrent request: {user_text}"

    def _compress_history_if_needed(self) -> None:
        """Real token-budget trigger, not an arbitrary turn count: the
        recent-turns-kept-verbatim window plus the running summary is what
        actually gets re-sent on every future turn, so THAT'S what has to
        stay under budget, not the full turn count."""
        verbatim_turns = self.turns[-self._recent_turns_kept_verbatim:]
        verbatim_text = "\n".join(f"{t.user_text} {t.response_text}" for t in verbatim_turns)
        estimated = estimate_tokens(self.running_summary) + estimate_tokens(verbatim_text)
        if estimated <= self._history_token_budget:
            return

        to_summarize = self.turns[: -self._recent_turns_kept_verbatim] if self._recent_turns_kept_verbatim else self.turns[:]
        if not to_summarize:
            return  # nothing older than the verbatim window to compress yet

        turns_text = "\n\n".join(
            f"User: {t.user_text}\nAssistant: {t.response_text}" for t in to_summarize
        )
        if self.running_summary:
            turns_text = f"Prior summary: {self.running_summary}\n\n{turns_text}"

        generator = RepairableGenerator(self._llm, _RunningSummary)
        result = generator.generate(SUMMARY_PROMPT.format(turns_text=turns_text))
        self.running_summary = result.summary

        # The summarized turns are now represented by running_summary --
        # keep only the still-verbatim window in self.turns going forward.
        self.turns = list(verbatim_turns)

    def _maybe_write_memory(self, turn: ConversationTurn) -> None:
        """Closes gap 2's write side: real MemoryWritePolicy gate, not an
        unconditional write. A high-importance candidate is queued for
        approval (self.pending_memory_approvals), never silently
        auto-written -- matching this project's standing human-in-the-loop
        principle (Phase 4's proposal/approval pattern)."""
        existing = self._memory_store.list_all(self._tenant_id, self._user_id)
        existing_summaries = [m.content for m in existing]

        conversation_text = f"User: {turn.user_text}\nAssistant: {turn.response_text}"
        candidate, requires_approval = self._write_policy.evaluate(conversation_text, existing_summaries)
        if candidate is None:
            return

        if requires_approval:
            self.pending_memory_approvals.append(
                PendingMemoryApproval(
                    turn_id=turn.turn_id, summary=candidate.summary or "",
                    memory_type=candidate.type, importance=candidate.importance,
                )
            )
            return

        self._write_memory(candidate.type, candidate.summary or "", candidate.importance, turn.turn_id)

    def approve_pending_memory(self, turn_id: str) -> MemoryRecord | None:
        """Explicit human approval path for a high-importance candidate
        queued by _maybe_write_memory -- mirrors
        app/actions/policy_engine.py's resume-after-approval pattern."""
        pending = next((p for p in self.pending_memory_approvals if p.turn_id == turn_id), None)
        if pending is None:
            return None
        self.pending_memory_approvals.remove(pending)
        return self._write_memory(pending.memory_type, pending.summary, pending.importance, turn_id)

    def _write_memory(self, memory_type, summary: str, importance: float, turn_id: str) -> MemoryRecord:
        now = datetime.now(timezone.utc)
        record = MemoryRecord(
            memory_id=f"session_{self.session_id}_{turn_id}",
            tenant_id=self._tenant_id, user_id=self._user_id,
            type=memory_type or MemoryType.EXPERIENCE, content=summary,
            source=f"conversation_session:{self.session_id}",
            created_at=now, updated_at=now, importance=importance, user_confirmed=False,
        )
        self._memory_store.write(record)
        return record
