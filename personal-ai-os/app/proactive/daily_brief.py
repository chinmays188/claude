from pydantic import BaseModel, Field

from app.proactive.attention import ScoredSignal
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

PROACTIVE_BRIEF_PROMPT = """Produce today's priorities using ONLY the ranked
signals below, which were already surfaced by the attention engine (highest
attention first). This is ADVISORY ONLY — suggest priorities for the user to
consider, never claim anything was done or will be done automatically. Do not
invent signals or details not present below.

Ranked signals (score, title, description):
{signals}

Respond with ONLY a JSON object:
{{"priorities": ["<a specific, actionable priority derived from a signal above, in suggested order>"]}}
"""


class ProactiveDailyBrief(BaseModel):
    priorities: list[str] = Field(default_factory=list)
    source_signal_ids: list[str] = Field(default_factory=list)


def generate_proactive_daily_brief(llm: LLMProvider, scored_signals: list[ScoredSignal]) -> ProactiveDailyBrief:
    """Milestone 32: unlike Phase 3's daily_brief.py (which takes manually-
    assembled source strings), this version is driven directly by the
    Attention Engine's ranked output (Milestone 31) — this is what makes it
    'proactive' rather than something the user has to ask for and assemble
    context for themselves."""
    if not scored_signals:
        return ProactiveDailyBrief(priorities=[], source_signal_ids=[])

    signals_text = "\n".join(
        f"- [{s.attention_score:.2f}] {s.signal.title}: {s.signal.description}" for s in scored_signals
    )
    generator = RepairableGenerator(llm, ProactiveDailyBrief)
    result = generator.generate(PROACTIVE_BRIEF_PROMPT.format(signals=signals_text))
    result.source_signal_ids = [s.signal.signal_id for s in scored_signals]
    return result
