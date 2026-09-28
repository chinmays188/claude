"""Generates REAL example GoalRuns and a REAL HarnessSuggestion for the
Chief of Staff dashboard page, run live once and committed as
app/dashboard_ui/cos_examples.json -- same pattern as example_traces.json
(the dashboard never makes a live LLM call itself).

Covers the two NEW Chief of Staff responsibilities added this session:
  - Goal-driven loop (app/proactive/goal_run.py): 2 real GoalRuns, one that
    achieves the goal in 1 iteration, one that runs out its max-iterations
    budget without ever being judged achieved -- both real, live runs
    through the real Orchestrator + a real GoalCompletionChecker call,
    not scripted.
  - Harness feedback (app/proactive/harness_feedback.py): 1 real
    HarnessSuggestion generated from the REAL error/failure data already
    committed in app/dashboard_ui/failure_traces.json and
    eval_history.json (loaded via the same seeding functions the dashboard
    itself uses), so the suggestion is grounded in real, inspectable
    evidence, not invented for this script.

Usage:
    PYTHONPATH=. python scripts/generate_cos_examples.py
"""

import json
import sqlite3
import time
from pathlib import Path

from app.agents.orchestrator import Orchestrator
from app.config import require_gemini_key
from app.dashboard_ui.example_traces import seed_example_traces
from app.dashboard_ui.failure_traces import seed_failure_traces
from app.domains.cross_domain.goal_agent import GoalAgent
from app.domains.cross_domain.goal_store import GoalStore
from app.domains.router import Domain
from app.observability.trace_store import TraceStore
from app.proactive.goal_run import GoalCompletionChecker, GoalRunner
from app.proactive.harness_feedback import generate_harness_suggestion
from app.providers.gemini_provider import GeminiProvider

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "cos_examples.json"
USER_ID = "demo_user"


def _load_eval_history() -> list[dict]:
    path = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "eval_history.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def main() -> None:
    require_gemini_key()
    llm = GeminiProvider()

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    goal_store = GoalStore(conn)
    goal_agent = GoalAgent(goal_store)
    orchestrator = Orchestrator(llm)
    checker = GoalCompletionChecker(llm)

    # Scenario 1: a real, simple request the agent genuinely satisfies in
    # one pass.
    runner_quick = GoalRunner(orchestrator, goal_agent, goal_store, checker, max_iterations=3)
    quick_run = runner_quick.run(USER_ID, "Explain what RAG is in one paragraph.", Domain.LEARNING)
    print(f"[1/2] Quick GoalRun: {quick_run.run_id} (achieved={quick_run.achieved}, "
          f"iterations={len(quick_run.iterations)}, stop_reason={quick_run.stop_reason})")

    time.sleep(20)  # stay under the real free-tier rate limit (15 req/min)

    # Scenario 2: a deliberately narrow max_iterations budget (1) against a
    # genuinely open-ended request, so the completion checker can honestly
    # judge "not fully achieved yet" and the real max_iterations backstop
    # is what actually stops the loop -- not a scripted failure.
    runner_bounded = GoalRunner(orchestrator, goal_agent, goal_store, checker, max_iterations=1)
    bounded_run = runner_bounded.run(
        USER_ID, "Create a complete 90-day plan to become a senior PM for AI-agent products.", Domain.CAREER,
    )
    print(f"[2/2] Bounded GoalRun: {bounded_run.run_id} (achieved={bounded_run.achieved}, "
          f"iterations={len(bounded_run.iterations)}, stop_reason={bounded_run.stop_reason})")

    time.sleep(20)

    # Real harness suggestion, grounded in the real committed failure
    # traces + eval history (loaded the same way the dashboard does).
    trace_conn = sqlite3.connect(":memory:")
    trace_conn.row_factory = sqlite3.Row
    trace_store = TraceStore(trace_conn)
    seed_example_traces(trace_store)
    seed_failure_traces(trace_store)
    summaries = trace_store.list_summaries(limit=200)
    traces = [trace_store.get(s["execution_id"]) for s in summaries]
    eval_history = _load_eval_history()
    goal_runs = [quick_run, bounded_run]

    suggestion = generate_harness_suggestion(llm, USER_ID, traces, eval_history, goal_runs)
    print(f"\nHarness suggestion (has_suggestion={suggestion.has_suggestion}): {suggestion.suggestion}")
    print(f"Evidence cited: {suggestion.evidence_cited}")

    out = {
        "goal_runs": [json.loads(r.model_dump_json()) for r in (quick_run, bounded_run)],
        "harness_suggestion": json.loads(suggestion.model_dump_json()),
    }
    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"\nWrote real CoS examples to {OUT_PATH}")


if __name__ == "__main__":
    main()
