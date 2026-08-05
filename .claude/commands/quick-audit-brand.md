---
description: "Quick quality audit of a draft article against brand voice and structure rules. Use /quick-audit <path> to check any draft."
user_invocable: true
---

# Quick Audit

Audit the following draft for quality: $ARGUMENTS

## Process
1. Read the draft file at the provided path
2. Check against brand voice rules:
   - No forbidden phrases (revolutionary, game-changing, unlock, unleash, supercharge, paradigm, next-level)
   - Paragraphs under 4 lines
   - First sentence under 10 words
   - Specific numbers in outcomes
3. Check structure:
   - Intro answers: what, problem, why, promise
   - Big idea statement present
   - Key takeaways are actionable bullets
   - Mini exercise included
4. Check readability: target Grade 8

## Output
- Overall score (1-10)
- Issues found (critical, major, minor)
- Specific fix suggestions with line numbers
