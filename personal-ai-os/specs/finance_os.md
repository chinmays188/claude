# Finance OS

## The one non-negotiable rule for this domain (Sections 23-25)

> Never use an LLM for arithmetic that can be performed deterministically.

Every number a user sees from Finance OS — total value, allocation percentage,
scenario loss, recovery return, loan payoff time, SIP projection — is computed
in `app/domains/finance/calculations.py`, pure Python, zero LLM calls. The LLM
is only ever asked to add *interpretation* (ASSUMPTION/OPINION claims), and is
explicitly instructed not to recompute or contradict the numbers it's given.

## Example 1 — Portfolio totals are exact, not estimated

Input:
A portfolio with two holdings (values 1200 and 500).

Expected:
- `portfolio_total_value()` returns exactly 1700 — deterministic arithmetic,
  reproducible, auditable
- `analyze_portfolio()`'s output includes this as a `FACT`-tagged claim with
  the actual computed value attached (`TaggedClaim.value`), not just prose

## Example 2 — Every claim is tagged FACT/CALCULATION/ASSUMPTION/OPINION

Input:
A portfolio analysis result.

Expected:
- `check_all_claims_tagged()` verifies every single claim has one of exactly
  4 tags — Section 23's core structural requirement, made checkable rather
  than just documented in a prompt
- `check_calculations_match_deterministic_values()` verifies a `CALCULATION`
  claim's stated numeric value actually matches what the deterministic
  calculator produced — catches an LLM silently "correcting" or restating a
  number wrong, the exact failure mode Section 24 exists to prevent

## Example 3 — Scenario analysis has no LLM dependency at all

Input:
"What happens if my portfolio falls 20%?"

Expected:
- `analyze_scenario()`'s function signature has no `llm` parameter —
  structurally incapable of calling an LLM for this workflow, not just
  instructed not to
- Recovery-return asymmetry is correct: a 20% loss (1000 -> 800) requires a
  25% gain to recover, not 20% — `recovery_return_required()` computes this
  exactly

## Example 4 — Loan payoff uses real amortization math

Input:
A $10,000 loan at 10% annual interest, $500/month payment.

Expected:
- `loan_payoff_months()` runs an actual amortization loop (interest accrual,
  principal reduction) rather than a rough estimate
- A payment too small to cover monthly interest raises `ValueError` rather
  than looping forever or returning a nonsensical negative payoff time

## Example 5 — No trade execution or fund transfer capability exists

Input:
Any call to `execute_trade()` or `transfer_funds()`, with any arguments.

Expected:
- Both always raise `TradeExecutionForbiddenError` — Section 25: "Never
  execute trades. Never transfer money." This is enforced as dead-end stub
  functions that fail loudly, not merely undocumented/unimplemented, so a
  hallucinated tool call or a future coding mistake can't accidentally wire
  up a working execution path
- `check_no_trade_execution_capability()` verifies this structurally

## Data note

All test portfolios/holdings/loans/goals are fabricated example data — no
real financial information, per project scope decision for this milestone.

## Non-goals for this milestone

- `investment_comparison` and `portfolio_drift` (Section 21's remaining
  skills) are not implemented as standalone functions — they're
  straightforward extensions of the same deterministic-calculation +
  tagged-claim pattern already established here.
- "Cite current external information" (Section 25) — no live market-data
  integration exists in this project; this constraint applies once/if a real
  price-feed integration is added.
