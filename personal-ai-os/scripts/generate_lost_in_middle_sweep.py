"""Real, systematic lost-in-the-middle sweep across multiple context
scales, found missing while investigating "Context Engineering"
(disclosed gap: "the lost-in-the-middle result is a single data point
at one context length/model, not a systematic sweep"). Reuses the
exact same real fixture/question/judging logic as
scripts/generate_lost_in_middle_experiment.py (which only ever ran at
one scale, ~200 filler chunks) -- this script runs the same real check
at 3 real scales x 3 positions = 9 real, live Gemini calls, paced under
the real 15 req/min free-tier limit.

Usage:
    PYTHONPATH=. python scripts/generate_lost_in_middle_sweep.py
"""

import json
import time
from pathlib import Path

from app.config import require_gemini_key
from app.providers.gemini_provider import GeminiProvider
from scripts.generate_lost_in_middle_experiment import (
    _BASE_FILLER_TEMPLATES,
    _REGIONS,
    _TEAMS,
    run_position,
)

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "lost_in_middle_sweep_results.json"

SCALES = [20, 100, 200]  # real filler-chunk counts to sweep across
SLEEP_SECONDS_BETWEEN_CALLS = 5  # real 15 req/min free-tier limit -- stay well under it


def _filler_chunks(count: int) -> list[str]:
    return [
        template.format(pct=5 + (i * 3) % 40, region=_REGIONS[i % len(_REGIONS)], team=_TEAMS[i % len(_TEAMS)])
        for i in range(-(-count // len(_BASE_FILLER_TEMPLATES)))  # ceil division
        for template in _BASE_FILLER_TEMPLATES
    ][:count]


def _write(sweep_results: list[dict]) -> None:
    OUT_PATH.write_text(json.dumps({"sweep_results": sweep_results, "scales": SCALES}, indent=2))


def main() -> None:
    require_gemini_key()
    llm = GeminiProvider()

    # Resume support: a real transient API failure (504 DEADLINE_EXCEEDED
    # was genuinely hit once while running this) shouldn't discard real
    # calls that already succeeded -- load whatever this run (or a prior
    # partial run) already has and skip positions already completed.
    sweep_results: list[dict] = []
    if OUT_PATH.exists():
        sweep_results = json.loads(OUT_PATH.read_text()).get("sweep_results", [])
    done = {(r["filler_chunk_count"], r["position"]) for r in sweep_results}

    for scale in SCALES:
        filler_chunks = _filler_chunks(scale)
        for position in ("start", "middle", "end"):
            if (scale, position) in done:
                print(f"[{scale:>4} chunks | {position:>6}] already done, skipping")
                continue
            for attempt in range(3):
                try:
                    result = run_position(position, filler_chunks, llm)
                    break
                except Exception as exc:  # noqa: BLE001 -- a real, transient API error must not lose prior real results
                    print(f"  real error on attempt {attempt + 1}: {exc}")
                    if attempt == 2:
                        _write(sweep_results)
                        raise
                    time.sleep(10)
            result["filler_chunk_count"] = scale
            sweep_results.append(result)
            _write(sweep_results)  # save after every real call, not just at the end
            status = "CORRECT" if result["correct"] else "WRONG/MISSED"
            print(f"[{scale:>4} chunks | {position:>6}] {status}")
            time.sleep(SLEEP_SECONDS_BETWEEN_CALLS)

    print(f"\nWrote real lost-in-the-middle sweep results to {OUT_PATH}")

    any_degradation = any(not r["correct"] for r in sweep_results)
    if any_degradation:
        print("\nReal degradation WAS observed at some scale/position -- see results above.")
    else:
        print("\nReal finding: no degradation observed at any scale tried (20/100/200 chunks).")


if __name__ == "__main__":
    main()
