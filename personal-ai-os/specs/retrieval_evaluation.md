# Retrieval Evaluation

## Example 1 — Recall

Input:
5 relevant chunks exist for a query; retrieval returns 4 of them (plus 1 irrelevant).

Expected:
- `recall == 0.8` (4/5)
- Recall is computed independently of whether the final LLM answer "sounds good"
  (Section 18)

## Example 2 — Precision

Input:
Retrieval returns 10 chunks; only 6 are actually relevant per the labeled case.

Expected:
- `precision == 0.6` (6/10)

## Example 3 — Grounding

Input:
An LLM-generated answer and the chunks that were retrieved for it.

Expected:
- `evaluate_grounding()` (LLM-as-judge) scores what fraction of the answer's
  claims are supported by the retrieved evidence, not by general world knowledge
- A hallucinated claim not present in any retrieved chunk lowers `groundedness_score`

## Example 4 — Attribution / Citation quality

Input:
An answer with citations mapping claims to chunk ids.

Expected:
- `citation_quality()` checks each cited chunk id actually exists among the
  chunks that were retrieved
- A citation pointing to a non-existent or unretrieved chunk id counts against
  quality (fabricated citation, Section 34's structured-output correctness applies
  to citations too, not just prose)

## Edge case — No relevant chunks labeled for a query

Expected:
- Recall is defined as 1.0 by convention (nothing to miss) rather than raising
  a division-by-zero error

## Edge case — No chunks retrieved at all

Expected:
- Precision is defined as 0.0 (not undefined/NaN) when nothing was retrieved
