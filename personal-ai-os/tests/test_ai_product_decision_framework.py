import pytest

from app.evaluation.ai_product_decision_framework import (
    DecisionTier,
    ProductDecisionInputs,
    recommend_tier,
    tier_rank,
)


def test_fixed_rules_problem_recommends_deterministic_logic():
    result = recommend_tier(ProductDecisionInputs(can_be_solved_with_fixed_rules=True))
    assert result.tier == DecisionTier.DETERMINISTIC_LOGIC


def test_labeled_data_without_nl_recommends_traditional_ml():
    result = recommend_tier(
        ProductDecisionInputs(has_enough_labeled_data_for_traditional_ml=True)
    )
    assert result.tier == DecisionTier.TRADITIONAL_ML


def test_plain_language_task_recommends_single_llm_call():
    result = recommend_tier(ProductDecisionInputs(needs_natural_language_understanding_or_generation=True))
    assert result.tier == DecisionTier.SINGLE_LLM_CALL


def test_needs_real_knowledge_recommends_rag():
    result = recommend_tier(
        ProductDecisionInputs(
            needs_natural_language_understanding_or_generation=True,
            needs_grounding_in_retrievable_knowledge=True,
        )
    )
    assert result.tier == DecisionTier.RAG


def test_needs_real_actions_recommends_tool_calling():
    result = recommend_tier(
        ProductDecisionInputs(
            needs_natural_language_understanding_or_generation=True,
            needs_to_take_real_actions_not_just_answer=True,
        )
    )
    assert result.tier == DecisionTier.TOOL_CALLING


def test_needs_coordinated_roles_recommends_multi_agent():
    result = recommend_tier(
        ProductDecisionInputs(
            needs_natural_language_understanding_or_generation=True,
            needs_to_take_real_actions_not_just_answer=True,
            needs_multiple_distinct_kinds_of_work_coordinated=True,
        )
    )
    assert result.tier == DecisionTier.MULTI_AGENT


def test_consequential_action_always_recommends_human_approval_even_with_multi_agent():
    result = recommend_tier(
        ProductDecisionInputs(
            needs_natural_language_understanding_or_generation=True,
            needs_to_take_real_actions_not_just_answer=True,
            needs_multiple_distinct_kinds_of_work_coordinated=True,
            action_is_consequential_or_hard_to_reverse=True,
        )
    )
    assert result.tier == DecisionTier.HUMAN_APPROVAL_REQUIRED


def test_consequential_single_agent_action_recommends_human_approval():
    result = recommend_tier(
        ProductDecisionInputs(
            needs_natural_language_understanding_or_generation=True,
            needs_to_take_real_actions_not_just_answer=True,
            action_is_consequential_or_hard_to_reverse=True,
        )
    )
    assert result.tier == DecisionTier.HUMAN_APPROVAL_REQUIRED


def test_zero_human_in_loop_low_risk_recommends_autonomous_execution():
    result = recommend_tier(
        ProductDecisionInputs(
            needs_natural_language_understanding_or_generation=True,
            needs_to_take_real_actions_not_just_answer=True,
            needs_zero_human_in_the_loop=True,
        )
    )
    assert result.tier == DecisionTier.AUTONOMOUS_EXECUTION


def test_real_project_scenario_tool_agent_with_calculator():
    """Mirrors this project's own real app/agents/tool_agent.py + calculator case."""
    result = recommend_tier(
        ProductDecisionInputs(
            needs_natural_language_understanding_or_generation=True,
            needs_to_take_real_actions_not_just_answer=True,
        )
    )
    assert result.tier == DecisionTier.TOOL_CALLING


def test_real_project_scenario_send_email_act_classified():
    """Mirrors this project's own real ActionClassifier default: send_email
    is ACT-classified, requiring approval."""
    result = recommend_tier(
        ProductDecisionInputs(
            needs_natural_language_understanding_or_generation=True,
            needs_to_take_real_actions_not_just_answer=True,
            action_is_consequential_or_hard_to_reverse=True,
        )
    )
    assert result.tier == DecisionTier.HUMAN_APPROVAL_REQUIRED


def test_no_tier_matches_raises_with_actionable_message():
    with pytest.raises(ValueError, match="more specific diagnosis"):
        recommend_tier(ProductDecisionInputs())


def test_every_decision_includes_a_real_failure_mode_explanation():
    result = recommend_tier(ProductDecisionInputs(needs_natural_language_understanding_or_generation=True))
    assert result.failure_mode_if_under_built


def test_tier_rank_orders_deterministic_logic_below_autonomous_execution():
    assert tier_rank(DecisionTier.DETERMINISTIC_LOGIC) < tier_rank(DecisionTier.AUTONOMOUS_EXECUTION)


def test_tier_rank_orders_tool_calling_below_multi_agent():
    assert tier_rank(DecisionTier.TOOL_CALLING) < tier_rank(DecisionTier.MULTI_AGENT)
