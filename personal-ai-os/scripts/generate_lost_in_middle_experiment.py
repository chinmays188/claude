"""Runs a REAL lost-in-the-middle experiment against the live Gemini API,
per the user's ask to push "Context Engineering" toward 90% by actually
running the experiment this codebase's own lost_in_middle.py module made
possible but never exercised (Section 28).

Before this script, app/context/lost_in_middle.py's build_positioned_context()
was a real, correctly-tested function -- but nothing had ever called it
against a real request to check whether answer quality actually degrades
based on where a critical fact sits in the context. This script is that
real check.

Design: a real critical fact (a made-up but internally consistent detail,
clearly synthetic per this project's convention of never fabricating real
personal data) is buried among real filler chunks (generic paragraphs
about unrelated topics) at 'start', 'middle', and 'end', and the same
question is asked against the real Gemini API each time. Correctness is
judged deterministically (does the real answer contain the fact's specific
value?), not by another LLM call -- keeps this experiment auditable, not
another black box.

Usage:
    PYTHONPATH=. python scripts/generate_lost_in_middle_experiment.py
"""

import json
from pathlib import Path

from app.config import require_gemini_key
from app.context.lost_in_middle import build_positioned_context
from app.providers.gemini_provider import GeminiProvider

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "lost_in_middle_results.json"

CRITICAL_FACT = "The project's internal codename for the Q3 launch is 'Project Marigold-7'."
QUESTION = "What is the internal codename for the Q3 launch mentioned in the document above?"
EXPECTED_ANSWER_SUBSTRING = "Marigold-7"

# Real, generic filler -- deliberately unrelated to the fact. A first pass
# at 20 chunks (~500 words) showed NO degradation at any position (all 3
# correct) -- an honest real result, but not informative about where this
# model's real limits are. Scaled up substantially (base templates x 10
# repetitions with varied numbers/teams, ~200 chunks / ~4500 words) to get
# genuinely close to where lost-in-the-middle effects are documented to
# appear, per the user's explicit choice to push further rather than stop
# at an inconclusive small-scale result.
_BASE_FILLER_TEMPLATES = [
    "The quarterly report noted a {pct}% change in customer satisfaction scores across the {region} region.",
    "Office relocation plans for the {team} team have been postponed until next fiscal year.",
    "The engineering team completed a migration of the build pipeline to a new CI provider for {team}.",
    "Marketing is running an A/B test on the new landing page copy for the {region} market this month.",
    "The onboarding checklist for new hires on the {team} team was updated to include a security module.",
    "Support ticket volume changed by {pct}% in the {region} region after the new help center launched.",
    "The design system's color palette was refreshed to improve accessibility for the {team} product.",
    "A vendor contract renewal for {team} tooling is under review by legal and procurement.",
    "The mobile app's crash rate in the {region} region improved after the last two patch releases.",
    "Weekly standup notes for {team} mentioned a minor delay in the analytics dashboard rollout.",
    "The finance team is finalizing a {pct}% budget adjustment for the {team} group next cycle.",
    "A customer advisory board session for the {region} market is scheduled for early next month.",
    "The data warehouse migration for {team} is roughly {pct}% complete per the latest update.",
    "HR announced updated hybrid work guidelines applicable to the {team} team.",
    "The infrastructure team is evaluating a new managed database service for {team}.",
    "Product feedback from the {region} user research round highlighted navigation confusion.",
    "A new intern cohort will join the {team} team starting next quarter.",
    "API rate-limiting rules were adjusted by {pct}% to accommodate {region} partner traffic.",
    "Localization work for the {region} market is ongoing across three languages for {team}.",
    "The annual security audit for {team} is scheduled for the last week of this quarter.",
]
_TEAMS = ["Platform", "Growth", "Payments", "Core", "Data", "Mobile", "Web", "Infra", "Search", "Support"]
_REGIONS = ["APAC", "EMEA", "LATAM", "NA", "ANZ", "MENA", "SEA", "Nordics", "DACH", "UKI"]

FILLER_CHUNKS = [
    template.format(pct=5 + (i * 3) % 40, region=_REGIONS[i % len(_REGIONS)], team=_TEAMS[i % len(_TEAMS)])
    for i in range(10)
    for template in _BASE_FILLER_TEMPLATES
]


def run_position(position: str, filler_chunks: list[str], llm: GeminiProvider) -> dict:
    context = build_positioned_context(filler_chunks, CRITICAL_FACT, position)
    prompt = f"{context}\n\n{QUESTION}"
    answer = llm.generate(prompt)

    correct = EXPECTED_ANSWER_SUBSTRING.lower() in answer.lower()
    return {
        "position": position,
        "context_char_length": len(context),
        "answer": answer,
        "correct": correct,
    }


def main() -> None:
    require_gemini_key()
    llm = GeminiProvider()

    results = [run_position(p, FILLER_CHUNKS, llm) for p in ("start", "middle", "end")]

    for r in results:
        status = "CORRECT" if r["correct"] else "WRONG/MISSED"
        print(f"[{r['position']:>6}] {status} -- answer: {r['answer'][:100]!r}")

    out = {
        "critical_fact": CRITICAL_FACT,
        "question": QUESTION,
        "expected_answer_substring": EXPECTED_ANSWER_SUBSTRING,
        "filler_chunk_count": len(FILLER_CHUNKS),
        "results": results,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nWrote real lost-in-the-middle results to {OUT_PATH}")


if __name__ == "__main__":
    main()
