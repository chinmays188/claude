import hashlib

from pydantic import BaseModel

from app.proactive.triggers import Signal


class ScoredSignal(BaseModel):
    signal: Signal
    attention_score: float  # 0.0-1.0
    reason: str


# Deterministic base weight per trigger — a design decision (not learned),
# auditable and adjustable, matching this project's preference for
# deterministic scoring wherever judgment isn't strictly required.
_TRIGGER_BASE_WEIGHT: dict[str, float] = {
    "goal_deadline_approaching": 0.9,
    "urgent_email": 0.85,
    "task_stuck": 0.6,
    # Deliberately lower than goal_deadline_approaching: a deadline-less
    # stalled goal is real but less urgent than one about to actually miss
    # a real deadline.
    "goal_stalled_no_deadline": 0.5,
}
_DEFAULT_WEIGHT = 0.4


class AttentionEngine:
    """Milestone 31: scores and deduplicates signals so the user is shown
    only what actually deserves attention, not every trigger firing. Section
    (Phase 4 core concepts): 'Attention scoring', 'Notification deduplication.'"""

    def __init__(self, dedup_window: int = 50):
        self._dedup_window = dedup_window
        self._seen_hashes: list[str] = []

    def score(self, signal: Signal) -> ScoredSignal:
        base = _TRIGGER_BASE_WEIGHT.get(signal.trigger_name, _DEFAULT_WEIGHT)
        return ScoredSignal(
            signal=signal, attention_score=base,
            reason=f"Base weight for trigger '{signal.trigger_name}'.",
        )

    def is_duplicate(self, signal: Signal) -> bool:
        """Dedup by (trigger_name, title) content hash — the same underlying
        issue (e.g. the same stuck task) firing repeatedly shouldn't produce a
        fresh notification each time."""
        digest = hashlib.sha256(f"{signal.trigger_name}::{signal.title}".encode()).hexdigest()
        if digest in self._seen_hashes:
            return True
        self._seen_hashes.append(digest)
        if len(self._seen_hashes) > self._dedup_window:
            self._seen_hashes.pop(0)
        return False

    def rank(self, signals: list[Signal], min_score: float = 0.0) -> list[ScoredSignal]:
        """Scores, deduplicates, filters below min_score, and sorts
        highest-attention-first. This is the function a Daily Brief or
        real-time notifier would actually call."""
        scored = []
        for signal in signals:
            if self.is_duplicate(signal):
                continue
            result = self.score(signal)
            if result.attention_score >= min_score:
                scored.append(result)
        return sorted(scored, key=lambda s: s.attention_score, reverse=True)
