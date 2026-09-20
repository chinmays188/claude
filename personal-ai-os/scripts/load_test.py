"""Milestone 56: Load & Performance Engineering.

A real, runnable load-test script exercising the FastAPI voice endpoint
in-process (via TestClient, so it works without a running server or network),
measuring p50/p95/p99 latency and error rate under concurrent load.

HONEST SCOPE NOTE: this measures the app's own request-handling latency
under synthetic concurrent load in this sandbox, using a scripted (fake) LLM
provider so it doesn't depend on live Gemini API latency/quota, and can run
without cost. It does NOT measure:
  - Real production infrastructure (load balancer, multiple real workers,
    real network latency) — none of that is deployed anywhere.
  - Real user traffic patterns — the request mix here is synthetic/uniform.
  - Live Gemini API latency under load — a real load test against the live
    API would need its own rate-limit-aware design and would cost money per
    request; deliberately out of scope for an automated, repeatable script.
This is the deepest load-testing artifact honestly buildable without a real
deployment target, per Phase 5's scope decision — a real production load test
against a real deployment is future work, not something this script can claim
to have done.

Usage:
    PYTHONPATH=. python scripts/load_test.py --requests 100 --concurrency 10
"""

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.agents.orchestrator import Orchestrator
from app.api.voice_api import app, get_session_store
from app.providers.base import LLMProvider
from app.voice.session import VoiceSessionStore


class FastScriptedProvider(LLMProvider):
    """A fake provider that always returns a valid, immediate response —
    isolates the load test to the app's own overhead (routing, validation,
    session handling) rather than LLM latency, which is a separate, external
    concern this script deliberately does not attempt to measure."""

    def generate(self, prompt: str) -> str:
        if "task_type" in prompt or "domains" in prompt:
            return '{"task_type": "research", "confidence": 0.9}'
        return '{"action": "final_answer", "answer": "Load test response."}'

    @property
    def model_name(self) -> str:
        return "fast-scripted-model"


def run_load_test(num_requests: int, concurrency: int) -> dict:
    store = VoiceSessionStore(orchestrator_factory=lambda: Orchestrator(llm=FastScriptedProvider()))
    app.dependency_overrides[get_session_store] = lambda: store
    client = TestClient(app)

    latencies_ms: list[float] = []
    errors = 0

    def one_request(i: int) -> None:
        start = time.monotonic()
        try:
            response = client.post("/voice/turn", json={"transcript": f"Explain concept {i}."})
            if response.status_code != 200:
                nonlocal errors
                errors += 1
        except Exception:
            errors += 1
        latencies_ms.append((time.monotonic() - start) * 1000)

    overall_start = time.monotonic()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        list(executor.map(one_request, range(num_requests)))
    overall_elapsed = time.monotonic() - overall_start

    app.dependency_overrides.clear()

    sorted_latencies = sorted(latencies_ms)
    return {
        "total_requests": num_requests,
        "concurrency": concurrency,
        "errors": errors,
        "error_rate": errors / num_requests,
        "total_time_seconds": overall_elapsed,
        "requests_per_second": num_requests / overall_elapsed,
        "p50_ms": sorted_latencies[int(len(sorted_latencies) * 0.50)],
        "p95_ms": sorted_latencies[int(len(sorted_latencies) * 0.95) - 1],
        "p99_ms": sorted_latencies[int(len(sorted_latencies) * 0.99) - 1],
        "mean_ms": statistics.mean(latencies_ms),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()

    results = run_load_test(args.requests, args.concurrency)
    print("Load test results (in-process, scripted LLM provider — see module docstring for scope):")
    for key, value in results.items():
        print(f"  {key}: {value:.3f}" if isinstance(value, float) else f"  {key}: {value}")
