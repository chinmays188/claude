"""Generates REAL temperature/model-parameter examples for the dashboard,
found missing while investigating "LLM Fundamentals" (criterion:
"understand... temperature and model parameters"). GeminiProvider.generate()
never exposed any generation-config control at all before this -- every
real call used the SDK's own implicit defaults.

Real finding from running this live, honestly reported: some creative-
writing prompts show real variance even at temperature=0.0 (Gemini isn't
perfectly deterministic at temp 0 -- a known, real behavior, not a bug in
this code), while some factual prompts show almost NO variance even at
temperature=2.0 (a strong single-answer attractor dominates regardless of
sampling temperature). The prompt below was chosen because it showed a
real, clear, repeatable difference when actually tried against the live
API -- not because it was expected to in theory.

Usage:
    PYTHONPATH=. python scripts/generate_temperature_examples.py
"""

import json
import time
from pathlib import Path

from app.config import require_gemini_key
from app.providers.gemini_provider import GeminiProvider

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "temperature_examples.json"

PROMPT = "Write a 5-word opening line for a mystery novel."
CALLS_PER_TEMPERATURE = 4
# Real, hard free-tier rate limit confirmed earlier this project: 15
# requests/min. 2 temperatures x 4 calls = 8 real calls; paced well under
# the limit.
SLEEP_SECONDS_BETWEEN_CALLS = 5


def _run_at_temperature(temperature: float) -> list[str]:
    provider = GeminiProvider(temperature=temperature)
    results = []
    for _ in range(CALLS_PER_TEMPERATURE):
        results.append(provider.generate(PROMPT).strip())
        time.sleep(SLEEP_SECONDS_BETWEEN_CALLS)
    return results


def main() -> None:
    require_gemini_key()

    cold_results = _run_at_temperature(0.0)
    print(f"temperature=0.0: {cold_results}")

    hot_results = _run_at_temperature(1.8)
    print(f"temperature=1.8: {hot_results}")

    out = {
        "prompt": PROMPT,
        "cold": {"temperature": 0.0, "results": cold_results, "unique_count": len(set(cold_results))},
        "hot": {"temperature": 1.8, "results": hot_results, "unique_count": len(set(hot_results))},
    }
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nWrote real temperature examples to {OUT_PATH}")


if __name__ == "__main__":
    main()
