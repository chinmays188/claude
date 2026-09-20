# Domain Router

## Example 1 — Single-domain routing

Input:
"What should I add to my resume?" / "Analyze this stakeholder request." /
"How is my portfolio allocated?" / "Teach me Kubernetes."

Expected:
- Routes to exactly one of `CAREER` / `PM` / `FINANCE` / `LEARNING` respectively
- Matches Section 5's four worked examples exactly

## Example 2 — Cross-domain routing

Input:
"Should I learn this technology for my career?"

Expected:
- `DomainClassification.domains == [CAREER, LEARNING]` (or any order)
- `is_cross_domain == True`
- The router does not force a single label onto a request that genuinely spans
  two domains (Section 5's own example) — this is a first-class output shape,
  not an edge case to special-case around

## Example 3 — Low confidence becomes unclear

Input:
A vague request the model classifies with confidence below the threshold
(default 0.5).

Expected:
- `domains == []`, `is_unclear == True` — same "don't guess when unsure"
  discipline as Phase 1's `TaskClassifier` (Milestone 2), extended to a
  multi-label classifier

## Example 4 — Empty input rejected before any LLM call

Input:
`""` or whitespace-only.

Expected:
- `ValueError` raised immediately — no wasted LLM call

## Example 5 — Malformed model output

Input:
The LLM repeatedly returns invalid JSON across all repair attempts
(`RepairableGenerator`, Milestone 4).

Expected:
- `DomainRoutingError` raised — never silently defaults to a domain or an
  empty-but-successful result

## Relationship to Phase 1's TaskClassifier

`DomainRouter` is a new, separate component from `app/routing/classifier.py`'s
`TaskClassifier` — that classifier picks exactly one of research/analysis/
planning and existing code (`Orchestrator`) depends on its single-label shape.
The Domain Router's multi-label requirement (Section 5) doesn't fit that
interface, so it's built alongside it rather than modifying `TaskClassifier`
and risking breaking Phase 1/2 callers.

## Non-goals for this milestone

- The router only classifies; it does not yet dispatch to domain agents (those
  don't exist yet — Career/PM/Finance/Learning OS are separate, later
  milestones in this phase).
