"""Generates REAL model-routing examples for the dashboard, per the user's
ask: "we are only using gemini for LLM call. what all needs to be done to
take the progress to 90%."

Checked first, honestly: app/routing/model_router.py's ModelRouter/
TaskComplexity existed, tested, but its own spec (specs/model_routing.md)
explicitly said "Not yet wired into Orchestrator/main.py." This project
was also confirmed to only ever call one Gemini tier in practice
(gemini-3.5-flash-lite) -- no real routing decision had ever actually
happened.

This script captures 2 REAL, live routing decisions (not simulated):
  1. A genuinely SIMPLE request -> routed to the cheap tier
     (gemini-3.5-flash-lite), real tokens/cost.
  2. A genuinely COMPLEX request (matches a real complexity signal) ->
     routed to the strong tier (gemini-3.8-flash), real tokens/cost.

The strong tier (gemini-3.8-flash) has a real, hard free-tier quota (20
requests/day, confirmed earlier this project) -- this script spends
exactly 1 real call against it, not more. The degraded-mode (fallback on
quota exhaustion) scenario is NOT captured via real quota exhaustion here
(deliberately, per the user's explicit choice) -- it's captured with a
scripted failing provider standing in for the strong tier, since the
fallback MECHANISM is already proven by real tests
(tests/test_routing_llm_provider.py); this just needs one real,
illustrative trace showing what a degraded response looks like end to end.

Usage:
    PYTHONPATH=. python scripts/generate_model_routing_examples.py
"""

import json
from pathlib import Path

from app.config import require_gemini_key
from app.providers.base import LLMProvider
from app.providers.gemini_provider import GeminiProvider
from app.routing.model_router import (
    CHEAP_MODEL,
    STRONG_MODEL,
    ModelRouter,
    RoutingLLMProvider,
    TaskComplexity,
    classify_task_complexity,
)

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "model_routing_examples.json"

SIMPLE_REQUEST = "What is 12 times 7?"
COMPLEX_REQUEST = (
    "Please give me a comprehensive, in-depth comparison of RAG versus fine-tuning, "
    "covering the trade-offs in cost, latency, and answer quality."
)


class _AlwaysFailsProvider(LLMProvider):
    """Stands in for the strong tier ONLY for the degraded-mode example --
    deliberately not real quota exhaustion (see this module's docstring for
    why). Named realistically so the resulting trace reads honestly as
    'gemini-3.8-flash (simulated failure)', not as if it were a real call."""

    @property
    def model_name(self) -> str:
        return "gemini-3.8-flash (simulated failure, not real quota exhaustion)"

    def generate(self, prompt: str) -> str:
        raise RuntimeError("Simulated failure standing in for real daily-quota exhaustion.")


def _run_real_example(request: str, cheap_llm: GeminiProvider, strong_llm: GeminiProvider) -> dict:
    router = ModelRouter(
        {
            TaskComplexity.SIMPLE: cheap_llm,
            TaskComplexity.COMPLEX: strong_llm,
            TaskComplexity.EVALUATION: strong_llm,
        }
    )
    provider = RoutingLLMProvider(router)
    answer = provider.generate(request)
    decision = provider.last_decision
    return {
        "request": request,
        "predicted_complexity": classify_task_complexity(request).value,
        "answer": answer,
        "routed_model": decision.model_name,
        "degraded": decision.degraded,
        "reason": decision.reason,
        "simulated": False,
    }


def _run_degraded_example(request: str, cheap_llm: GeminiProvider) -> dict:
    router = ModelRouter(
        {
            TaskComplexity.SIMPLE: cheap_llm,
            TaskComplexity.COMPLEX: _AlwaysFailsProvider(),
            TaskComplexity.EVALUATION: _AlwaysFailsProvider(),
        }
    )
    provider = RoutingLLMProvider(router)
    answer = provider.generate(request)
    decision = provider.last_decision
    return {
        "request": request,
        "predicted_complexity": classify_task_complexity(request).value,
        "answer": answer,
        "routed_model": decision.model_name,
        "degraded": decision.degraded,
        "reason": decision.reason,
        "simulated": True,
    }


def main() -> None:
    require_gemini_key()
    cheap_llm = GeminiProvider(model=CHEAP_MODEL, track_usage=True)
    strong_llm = GeminiProvider(model=STRONG_MODEL, track_usage=True)

    simple_result = _run_real_example(SIMPLE_REQUEST, cheap_llm, strong_llm)
    print(f"[SIMPLE]  routed to {simple_result['routed_model']} -- {simple_result['answer'][:80]!r}")

    complex_result = _run_real_example(COMPLEX_REQUEST, cheap_llm, strong_llm)
    print(f"[COMPLEX] routed to {complex_result['routed_model']} -- {complex_result['answer'][:80]!r}")

    degraded_result = _run_degraded_example(COMPLEX_REQUEST, cheap_llm)
    print(f"[DEGRADED, simulated] routed to {degraded_result['routed_model']} -- "
          f"{degraded_result['answer'][:80]!r}")

    out = {
        "cheap_model": CHEAP_MODEL,
        "strong_model": STRONG_MODEL,
        "examples": [simple_result, complex_result, degraded_result],
        "real_usage": {
            "cheap_tier_calls": [u.model_dump() for u in cheap_llm.usage_log],
            "strong_tier_calls": [u.model_dump() for u in strong_llm.usage_log],
        },
    }
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nWrote real model-routing examples to {OUT_PATH}")


if __name__ == "__main__":
    main()
