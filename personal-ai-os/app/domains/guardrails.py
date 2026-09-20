"""Section 38's domain guardrails, consolidated as a registry pointing to
where each rule is actually enforced. This module adds NO new enforcement
logic — every rule listed here is already structurally enforced inside its
own domain (a grounding check, a fabrication check, a tagging requirement, a
raised exception). This registry exists so "what are all of Phase 3's
fabrication/safety rules, and where do I find each one" has a single answer,
rather than requiring someone to read all four domains' code to find out."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailRule:
    domain: str
    rule: str
    enforced_by: str  # module.function or class where this is actually checked


DOMAIN_GUARDRAILS: list[GuardrailRule] = [
    # Career (Section 38: never invent experience/achievements/employment history/metrics)
    GuardrailRule(
        domain="CAREER", rule="Never invent achievements in resume suggestions",
        enforced_by="app.domains.career.resume_optimization.check_resume_suggestions_grounded",
    ),
    GuardrailRule(
        domain="CAREER", rule="Never invent interview experience/stories",
        enforced_by="app.domains.career.interview_prep.build_interview_story (raises NoRelevantExperienceError)",
    ),
    # PM (Section 38: never fabricate customer data/product metrics/stakeholder statements/experiment results)
    GuardrailRule(
        domain="PM", rule="Never fabricate customer feedback themes",
        enforced_by="app.evaluation.pm_eval.check_feedback_themes_grounded",
    ),
    GuardrailRule(
        domain="PM", rule="PRD Critic must substantively challenge, not rubber-stamp",
        enforced_by="app.evaluation.pm_eval.check_critic_challenged_the_prd",
    ),
    GuardrailRule(
        domain="PM", rule="Never auto-modify Jira/PM tools without approval",
        enforced_by="app.domains.pm.sprint_planner (no write method exists; real writes go through app.actions.policy_engine.PolicyEngine)",
    ),
    # Finance (Section 38: never fabricate prices/returns/holdings/market information; Section 25's broader safety list)
    GuardrailRule(
        domain="FINANCE", rule="Every claim tagged FACT/CALCULATION/ASSUMPTION/OPINION",
        enforced_by="app.evaluation.finance_eval.check_all_claims_tagged",
    ),
    GuardrailRule(
        domain="FINANCE", rule="Calculations must match deterministic values, never LLM arithmetic",
        enforced_by="app.evaluation.finance_eval.check_calculations_match_deterministic_values",
    ),
    GuardrailRule(
        domain="FINANCE", rule="Never execute trades or transfer funds",
        enforced_by="app.domains.finance.safety.execute_trade / transfer_funds (always raise)",
    ),
    # Learning (Section 38: clearly distinguish factual explanation / analogy / speculation)
    GuardrailRule(
        domain="LEARNING", rule="Content tagged factual/analogy/speculation",
        enforced_by="app.evaluation.learning_eval.check_content_kind_labeled",
    ),
]


def rules_for_domain(domain: str) -> list[GuardrailRule]:
    return [r for r in DOMAIN_GUARDRAILS if r.domain == domain.upper()]
