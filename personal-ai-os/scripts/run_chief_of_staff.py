"""Actually activates Chief of Staff against the real GoalStore, per the
user's ask: "activate the chief of staff now... chief of staff needs to
track progress against all 15 project based learning goals."

This wires together real, already-tested Phase 4 components that existed
but were never connected end to end against real goal data (confirmed by
checking: GoalMonitor was previously exercised only in tests, never run
against the real seeded GoalStore):

    GoalStore (real, 15 real learning goals)
        -> GoalAgent.recommend_priorities() (deterministic ranking)
        -> GoalMonitor.check_goals() (Goal -> GOAL_UPDATED Event)
        -> TriggerEngine (GoalDeadlineApproachingTrigger +
           StalledGoalTrigger -- the latter is new, built specifically
           because all 15 learning goals have no deadline, so the
           deadline trigger alone would never fire for any of them)
        -> AttentionEngine (dedup + rank by real, deterministic weight)
        -> DecisionEngine (1 real LLM call per surfaced signal: how much
           response does this deserve?)
        -> ChiefOfStaffOrchestrator (sequences all of the above; never
           executes anything itself -- Phase 4's core rule)

Usage:
    PYTHONPATH=. python scripts/run_chief_of_staff.py
"""

from app.db.connection import get_connection
from app.domains.cross_domain.goal_agent import GoalAgent
from app.domains.cross_domain.goal_store import GoalStore
from app.proactive.attention import AttentionEngine
from app.proactive.builtin_triggers import GoalDeadlineApproachingTrigger, StalledGoalTrigger
from app.proactive.chief_of_staff import ChiefOfStaffOrchestrator
from app.proactive.decision_engine import DecisionEngine
from app.proactive.goal_monitor import GoalMonitor
from app.proactive.triggers import TriggerEngine
from app.providers.gemini_provider import GeminiProvider

DB_PATH = "data/personal_ai.db"
USER_ID = "demo_user"  # matches scripts/seed_demo_data.py / user_learning_goals.py

# Tools this Chief of Staff run is allowed to mention in a proposed plan.
# Kept deliberately small and safe -- action_plans.py's propose_plan()
# rejects any tool name not in this list, so this is a real safety boundary,
# not just documentation.
AVAILABLE_TOOL_NAMES = ["calculator", "retrieve", "analyze_feedback"]


def _print_header(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main() -> None:
    conn = get_connection(DB_PATH)
    goal_store = GoalStore(conn)
    goal_agent = GoalAgent(goal_store)
    goal_monitor = GoalMonitor(goal_agent)

    _print_header("1. GOAL MONITOR -- GoalStore -> GOAL_UPDATED events")
    events = goal_monitor.check_goals(USER_ID)
    print(f"Generated {len(events)} GOAL_UPDATED event(s) from real GoalStore data.")

    trigger_engine = TriggerEngine([
        GoalDeadlineApproachingTrigger(),
        StalledGoalTrigger(staleness_days=7, progress_threshold=0.7),
    ])
    attention_engine = AttentionEngine()

    llm = GeminiProvider()
    decision_engine = DecisionEngine(llm)

    orchestrator = ChiefOfStaffOrchestrator(
        trigger_engine=trigger_engine, attention_engine=attention_engine,
        decision_engine=decision_engine, llm=llm, available_tool_names=AVAILABLE_TOOL_NAMES,
    )

    _print_header("2. CHIEF OF STAFF -- observe -> understand -> prioritize -> propose")
    result = orchestrator.process(events)

    print(f"Signals raised: {len(result.scored_signals)}")
    if not result.scored_signals:
        print("No goal currently meets a trigger's threshold (deadline-approaching or "
              "stalled-without-deadline) -- nothing surfaced this run. This is a real "
              "outcome, not a failure: Chief of Staff only speaks up when a real "
              "condition is met.")
        return

    for scored, decision in zip(result.scored_signals, result.decisions):
        print(f"\n[{scored.attention_score:.2f}] {scored.signal.title}")
        print(f"  {scored.signal.description}")
        print(f"  Trigger: {scored.signal.trigger_name}")
        print(f"  Decision: {decision.response_type.value} -- {decision.reasoning}")

    if result.proposed_plans:
        _print_header("3. PROPOSED PLANS (require approval -- nothing auto-executes)")
        for plan in result.proposed_plans:
            print(f"\nPlan for signal {plan.triggered_by_signal_id}:")
            for step in plan.steps:
                print(f"  - [{step.status.value}] {step.tool_name}({step.args}): {step.description}")


if __name__ == "__main__":
    main()
