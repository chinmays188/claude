from datetime import datetime, timedelta, timezone

from app.context.personal_context_engine import PersonalContextEngine
from app.conversation.context_selection import build_context_items, select_context_text
from app.conversation.session import ConversationTurn
from app.memory.models import MemoryRecord, MemoryType
from app.memory.retrieval import RankedMemory

NOW = datetime.now(timezone.utc)


def _memory(content: str, importance: float, confidence: float = 1.0, age_days: float = 0.0) -> MemoryRecord:
    updated_at = NOW - timedelta(days=age_days)
    return MemoryRecord(
        memory_id="m1", tenant_id="t1", user_id="u1", type=MemoryType.PREFERENCE, content=content,
        source="test", created_at=updated_at, updated_at=updated_at, importance=importance, confidence=confidence,
    )


def test_build_context_items_includes_summary_turns_and_memories():
    turn = ConversationTurn(user_text="hi", response_text="hello")
    ranked = [RankedMemory(memory=_memory("likes bullet points", 0.8), score=0.9)]

    items = build_context_items("a running summary", [turn], ranked, now=NOW)

    sources = {i.source for i in items}
    assert sources == {"history_summary", "history_turn", "memory"}


def test_build_context_items_reuses_real_memory_retriever_score_as_relevance():
    ranked = [RankedMemory(memory=_memory("x", 0.5), score=0.73)]

    items = build_context_items("", [], ranked, now=NOW)

    assert items[0].relevance == 0.73


def test_low_relevance_memory_is_genuinely_excluded_under_tight_budget():
    """The real 'minimum useful context, not maximum' proof: a low-score
    memory competes against a high-score one for a tight budget and loses,
    for real -- not formatted differently, actually left out."""
    engine = PersonalContextEngine()
    high = RankedMemory(memory=_memory("Extremely relevant fact about the current question", 0.9), score=0.95)
    low = RankedMemory(memory=_memory("An old, barely related aside from months ago", 0.2, age_days=200), score=0.05)

    text, selected, excluded = select_context_text(engine, "", [], [high, low], token_budget=8)

    assert "Extremely relevant fact" in text
    assert "barely related aside" not in text
    assert any(i.source == "memory" and "barely related" in i.content for i in excluded)


def test_generous_budget_includes_everything():
    engine = PersonalContextEngine()
    ranked = [RankedMemory(memory=_memory("fact one", 0.8), score=0.9)]
    turn = ConversationTurn(user_text="q", response_text="a")

    text, selected, excluded = select_context_text(engine, "a summary", [turn], ranked, token_budget=10_000)

    assert "a summary" in text
    assert "fact one" in text
    assert excluded == []


def test_zero_budget_excludes_everything():
    engine = PersonalContextEngine()
    ranked = [RankedMemory(memory=_memory("fact", 0.8), score=0.9)]

    text, selected, excluded = select_context_text(engine, "summary", [], ranked, token_budget=0)

    assert text == ""
    assert selected == []
    assert len(excluded) == 2  # summary + memory item, both excluded


def test_ordering_is_summary_then_history_then_memory_regardless_of_score():
    """Ordering (Section 21) is a separate real decision from selection --
    even if a memory scores higher than the summary, the rendered text
    still places summary first, matching ContextBuilder's own declared
    section order convention."""
    engine = PersonalContextEngine()
    ranked = [RankedMemory(memory=_memory("very relevant fact", 0.9), score=0.99)]

    text, selected, excluded = select_context_text(engine, "a summary", [], ranked, token_budget=10_000)

    assert text.index("a summary") < text.index("very relevant fact")
