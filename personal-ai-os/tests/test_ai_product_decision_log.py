import subprocess
from pathlib import Path

from app.evaluation.ai_product_decision_framework import DecisionTier
from app.evaluation.ai_product_decision_log import (
    DECISION_LOG,
    decisions_by_tier,
    get_decision,
    tier_distribution,
)


def test_decision_log_has_a_meaningful_number_of_real_entries():
    assert len(DECISION_LOG) >= 10


def test_every_decision_has_a_unique_id():
    ids = [d.decision_id for d in DECISION_LOG]
    assert len(ids) == len(set(ids))


def test_every_decision_has_real_non_empty_content():
    for decision in DECISION_LOG:
        assert decision.title
        assert decision.what_was_chosen
        assert decision.what_was_rejected
        assert decision.real_rationale
        assert decision.source


def test_every_decision_cites_a_real_commit_hash_or_spec_file():
    """Every source must resolve to something real -- a real commit hash
    that actually exists in this repo's git history, or a real
    specs/*.md file -- never an invented citation."""
    for decision in DECISION_LOG:
        source = decision.source
        if source.endswith(".md"):
            assert (Path(__file__).resolve().parent.parent / source).exists(), (
                f"{decision.decision_id} cites a spec file that doesn't exist: {source}"
            )
        else:
            result = subprocess.run(
                ["git", "log", "-1", "--oneline", source],
                capture_output=True, text=True,
            )
            assert result.returncode == 0 and result.stdout.strip(), (
                f"{decision.decision_id} cites a commit hash that doesn't exist in this repo: {source}"
            )


def test_get_decision_returns_the_real_matching_entry():
    decision = get_decision("dual_router_to_unified")
    assert decision is not None
    assert decision.tier == DecisionTier.SINGLE_LLM_CALL


def test_get_decision_returns_none_for_unknown_id():
    assert get_decision("not_a_real_decision_id") is None


def test_decisions_by_tier_filters_correctly():
    tool_calling_decisions = decisions_by_tier(DecisionTier.TOOL_CALLING)
    assert all(d.tier == DecisionTier.TOOL_CALLING for d in tool_calling_decisions)
    assert len(tool_calling_decisions) >= 1


def test_tier_distribution_sums_to_real_total_count():
    distribution = tier_distribution()
    assert sum(distribution.values()) == len(DECISION_LOG)
