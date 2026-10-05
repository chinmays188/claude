"""The real AI Product Strategy decision framework this project's own
learning goal names but never had a dedicated artifact for: "Be able to
answer: should this be AI? should this be an agent? should we use RAG?
should we fine-tune? should this be multi-agent? should AI take the
action? ... Internalize the decision framework: deterministic logic ->
traditional ML -> LLM -> RAG -> tool calling -> agent -> multi-agent ->
human approval -> autonomous execution."

Checked first, honestly: app/evaluation/adaptation_advisor.py already
codified ONE real, narrow slice of this (RAG vs fine-tuning vs in-context
learning vs distillation, Section 57) -- correct, tested, but only one
rung of the full chain the learning goal actually names. This module is
the rest of the chain, built the same way: explicit, testable if/then
logic over real signals, not a model to train, and not vague prose.

Each tier answers one real question, in the real order a product
decision should actually ask them (cheapest/most deterministic first --
Section: "the question is the minimum useful context/capability, not the
maximum"):
  1. Can this be solved with plain deterministic code?
  2. Can this be solved with a simple, traditional ML model (classification/
     regression), not an LLM at all?
  3. Does it need an LLM, but a single call is enough (no retrieval, no
     tools, no multi-step reasoning)?
  4. Does it need grounding in real, retrievable knowledge (RAG)?
  5. Does it need to actually DO something via tool calls, not just
     answer?
  6. Does it need multiple distinct kinds of work (research + analysis +
     planning) coordinated together?
  7. Is the action consequential enough that a human must approve it
     before it executes?
  8. Can it run fully autonomously, with no human in the loop?

This is deliberately a DIAGNOSTIC tool (what tier does a described need
fall into), not a recommendation to always climb the ladder -- the
project's own real practice (reinforced across dozens of real decisions
in app/evaluation/ai_product_decision_log.py) is the opposite: use the
LOWEST tier that genuinely solves the real problem, and only move up when
a real, named signal requires it.
"""

from enum import Enum

from pydantic import BaseModel


class DecisionTier(str, Enum):
    DETERMINISTIC_LOGIC = "deterministic_logic"
    TRADITIONAL_ML = "traditional_ml"
    SINGLE_LLM_CALL = "single_llm_call"
    RAG = "rag"
    TOOL_CALLING = "tool_calling"
    AGENT = "agent"
    MULTI_AGENT = "multi_agent"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"
    AUTONOMOUS_EXECUTION = "autonomous_execution"


# Real, fixed ordering -- "how far up the chain" a tier sits, used to
# answer "is X a bigger commitment than Y" without re-deriving it.
_TIER_ORDER = list(DecisionTier)


class ProductDecisionInputs(BaseModel):
    """Real signals a PM can actually observe about a problem BEFORE
    picking an architecture -- every field maps to one real question in
    this module's own docstring, in the same order."""

    can_be_solved_with_fixed_rules: bool = False
    has_enough_labeled_data_for_traditional_ml: bool = False
    needs_natural_language_understanding_or_generation: bool = False
    needs_grounding_in_retrievable_knowledge: bool = False
    needs_to_take_real_actions_not_just_answer: bool = False
    needs_multiple_distinct_kinds_of_work_coordinated: bool = False
    action_is_consequential_or_hard_to_reverse: bool = False
    needs_zero_human_in_the_loop: bool = False


class ProductDecision(BaseModel):
    tier: DecisionTier
    reasoning: str
    # The real, concrete failure mode of choosing a tier BELOW this one --
    # i.e. what would actually go wrong if you under-built. Makes "why
    # not just use a cheaper approach" answerable, not asserted.
    failure_mode_if_under_built: str


def recommend_tier(inputs: ProductDecisionInputs) -> ProductDecision:
    """Real, explicit if/then logic, checked in the real order a product
    decision should ask these questions -- cheapest/most deterministic
    first, only climbing the chain when a real signal requires it."""

    if inputs.can_be_solved_with_fixed_rules:
        return ProductDecision(
            tier=DecisionTier.DETERMINISTIC_LOGIC,
            reasoning="The problem is fully specifiable as fixed rules -- no learning or "
                      "language understanding is actually needed.",
            failure_mode_if_under_built="N/A -- this is already the cheapest, most "
                                         "deterministic, most auditable tier.",
        )

    if inputs.has_enough_labeled_data_for_traditional_ml and not inputs.needs_natural_language_understanding_or_generation:
        return ProductDecision(
            tier=DecisionTier.TRADITIONAL_ML,
            reasoning="Real labeled data exists and the task is a classification/regression "
                      "problem, not natural language understanding or generation -- a "
                      "traditional ML model is cheaper, faster, and more interpretable than "
                      "an LLM for this shape of problem.",
            failure_mode_if_under_built="Deterministic rules would be too brittle to capture "
                                         "the real statistical pattern in the data.",
        )

    if not inputs.needs_natural_language_understanding_or_generation:
        raise ValueError(
            "No tier matched below the LLM tiers -- if natural language understanding/"
            "generation genuinely isn't needed, this problem needs a more specific "
            "diagnosis (deterministic logic or traditional ML) before an LLM-based tier "
            "applies at all."
        )

    if not inputs.needs_grounding_in_retrievable_knowledge and not inputs.needs_to_take_real_actions_not_just_answer:
        return ProductDecision(
            tier=DecisionTier.SINGLE_LLM_CALL,
            reasoning="Natural language understanding/generation is needed, but the request "
                      "doesn't need grounding in retrievable knowledge or real actions -- "
                      "the model's own training knowledge and reasoning are enough.",
            failure_mode_if_under_built="Deterministic rules or traditional ML can't handle "
                                         "open-ended natural language.",
        )

    if inputs.needs_grounding_in_retrievable_knowledge and not inputs.needs_to_take_real_actions_not_just_answer:
        return ProductDecision(
            tier=DecisionTier.RAG,
            reasoning="The answer needs to be grounded in real, retrievable knowledge "
                      "(fresh, specific, or proprietary information the model wasn't "
                      "trained on) but doesn't need to take real actions.",
            failure_mode_if_under_built="A single LLM call would hallucinate facts it "
                                         "wasn't actually trained on, or give stale answers "
                                         "for fast-changing information.",
        )

    if inputs.needs_to_take_real_actions_not_just_answer and not inputs.needs_multiple_distinct_kinds_of_work_coordinated:
        if inputs.action_is_consequential_or_hard_to_reverse:
            return ProductDecision(
                tier=DecisionTier.HUMAN_APPROVAL_REQUIRED,
                reasoning="The task needs to call tools/take real actions, and at least one "
                          "of those actions is consequential or hard to reverse -- a human "
                          "approval gate is required before execution, not just a capability "
                          "check.",
                failure_mode_if_under_built="An agent or tool-calling tier alone would let a "
                                             "consequential, hard-to-reverse action execute "
                                             "with no human in the loop.",
            )
        if inputs.needs_zero_human_in_the_loop:
            return ProductDecision(
                tier=DecisionTier.AUTONOMOUS_EXECUTION,
                reasoning="The task needs to take real actions, those actions are low-risk/"
                          "reversible, and the real requirement is zero human involvement "
                          "per execution.",
                failure_mode_if_under_built="A human-approval gate would add real friction "
                                             "to a task that genuinely doesn't need it, "
                                             "defeating the point of automating it.",
            )
        return ProductDecision(
            tier=DecisionTier.TOOL_CALLING,
            reasoning="The task needs to call real tools (retrieve, compute, look up), but "
                      "it's a single, bounded decision loop -- no need for multiple "
                      "coordinated specialist roles.",
            failure_mode_if_under_built="RAG or a single LLM call alone can't actually DO "
                                         "anything -- they can only answer.",
        )

    if inputs.needs_multiple_distinct_kinds_of_work_coordinated:
        if inputs.action_is_consequential_or_hard_to_reverse:
            return ProductDecision(
                tier=DecisionTier.HUMAN_APPROVAL_REQUIRED,
                reasoning="Multiple coordinated specialist roles are needed, AND at least "
                          "one resulting action is consequential/hard to reverse -- the "
                          "approval gate still applies on top of the multi-agent "
                          "coordination, not instead of it.",
                failure_mode_if_under_built="Multi-agent coordination alone doesn't add a "
                                             "safety gate -- a consequential action could "
                                             "still execute with no human review.",
            )
        return ProductDecision(
            tier=DecisionTier.MULTI_AGENT,
            reasoning="The task genuinely needs multiple distinct kinds of work "
                      "(research + analysis + planning, etc.) coordinated together, not "
                      "just one agent with a broader tool list.",
            failure_mode_if_under_built="A single agent would have to context-switch "
                                         "between genuinely different reasoning modes in "
                                         "one decision loop, degrading quality on each.",
        )

    return ProductDecision(
        tier=DecisionTier.AGENT,
        reasoning="A single decision loop with real tool access is needed, but none of the "
                  "stronger signals (multi-role coordination, consequential action, "
                  "autonomy requirement) apply.",
        failure_mode_if_under_built="Tool calling alone (a fixed sequence) can't adapt its "
                                     "own next step based on what a prior tool call "
                                     "returned.",
    )


def tier_rank(tier: DecisionTier) -> int:
    """0 = cheapest/most deterministic, higher = a bigger real commitment.
    Lets a caller ask 'is tier A a bigger commitment than tier B' without
    re-deriving the chain's order."""
    return _TIER_ORDER.index(tier)
