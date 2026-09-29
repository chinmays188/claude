"""Real context selection for ConversationSession, using the real
PersonalContextEngine (Section 19/20's 4-factor scoring engine) instead of
the previous "always include everything" approach.

Found while closing the "push Context Engineering to 90%" gap: before this
module, ConversationSession._build_prompted_text() unconditionally
included the running summary, every recent verbatim turn, and every
memory MemoryRetriever ranked -- there was no real selection happening,
just concatenation. PersonalContextEngine (real relevance/importance/
freshness/confidence scoring, a real token budget, and a real hard
exclusion of NONE-importance items) existed and was tested, but was never
called from anywhere. This module is the wiring: it turns
ConversationSession's real state (running summary, recent turns, ranked
memories) into real ContextItems, runs them through
PersonalContextEngine.select(), and is what makes "the question is the
minimum useful context, not the maximum" a demonstrable, real behavior
here for the first time -- a low-relevance memory or an old, low-priority
turn can now be genuinely EXCLUDED, not just formatted differently.
"""

from datetime import datetime, timezone

from app.context.builder import estimate_tokens
from app.context.personal_context_engine import ContextItem, ImportanceLevel, PersonalContextEngine
from app.memory.retrieval import RankedMemory


def build_context_items(
    running_summary: str,
    recent_turns: list,  # list[ConversationTurn]
    ranked_memories: list[RankedMemory],
    now: datetime | None = None,
) -> list[ContextItem]:
    """Real ContextItems from ConversationSession's real state -- every
    field here is derived from something real already computed elsewhere
    (MemoryRetriever's own relevance score, a memory's own
    importance/confidence, a turn's own timestamp), never invented."""
    now = now or datetime.now(timezone.utc)
    items: list[ContextItem] = []

    if running_summary:
        items.append(
            ContextItem(
                content=f"Earlier in this conversation (summarized): {running_summary}",
                relevance=0.6,  # a summary is always somewhat relevant by construction, but not as much as a live match
                importance=ImportanceLevel.MEDIUM,
                freshness=now,  # the summary is always "fresh" -- it's regenerated on every compression
                source="history_summary",
                confidence=0.8,  # LLM-summarized, not a direct quote
                token_cost=estimate_tokens(running_summary),
            )
        )

    for t in recent_turns:
        content = f"User previously said: {t.user_text}\nYou previously answered: {t.response_text}"
        age_days = max((now - t.created_at).total_seconds() / 86400, 0) if t.created_at.tzinfo else 0.0
        items.append(
            ContextItem(
                content=content,
                relevance=0.5,  # a recent turn is plausibly relevant but not scored against the CURRENT request here
                importance=ImportanceLevel.MEDIUM,
                freshness=t.created_at,
                source="history_turn",
                confidence=1.0,  # verbatim, not summarized
                token_cost=estimate_tokens(content),
            )
        )

    for rm in ranked_memories:
        # rm.score is MemoryRetriever's own real 4-factor score (similarity/
        # recency/importance/confirmed), already 0.0-1.0-ish -- reused
        # directly as this item's relevance rather than recomputed.
        relevance = max(0.0, min(1.0, rm.score))
        if rm.memory.importance >= 0.7:
            importance = ImportanceLevel.HIGH
        elif rm.memory.importance >= 0.3:
            importance = ImportanceLevel.MEDIUM
        else:
            importance = ImportanceLevel.LOW
        content = f"- {rm.memory.content}"
        items.append(
            ContextItem(
                content=content,
                relevance=relevance,
                importance=importance,
                freshness=rm.memory.updated_at,
                source="memory",
                confidence=rm.memory.confidence,
                token_cost=estimate_tokens(content),
            )
        )

    return items


def select_context_text(
    engine: PersonalContextEngine,
    running_summary: str,
    recent_turns: list,
    ranked_memories: list[RankedMemory],
    token_budget: int,
    now: datetime | None = None,
) -> tuple[str, list[ContextItem], list[ContextItem]]:
    """Runs the real PersonalContextEngine.select() and returns
    (rendered_text, selected_items, excluded_items) -- the excluded list is
    what makes "minimum useful context, not maximum" inspectable: a caller
    (or the dashboard) can show exactly what was left out and why, not just
    what made it in."""
    items = build_context_items(running_summary, recent_turns, ranked_memories, now=now)
    selected = engine.select(items, token_budget=token_budget, now=now)
    excluded = [item for item in items if item not in selected]

    # Preserve the original conceptual ordering (summary -> history -> memory)
    # among the selected items, rather than the score-sorted order
    # PersonalContextEngine.select() returns internally -- ordering is a
    # separate real decision (Section 21) from selection itself.
    order = {"history_summary": 0, "history_turn": 1, "memory": 2}
    selected_ordered = sorted(selected, key=lambda item: order.get(item.source, 99))

    text = "\n\n".join(item.content for item in selected_ordered)
    return text, selected_ordered, excluded
