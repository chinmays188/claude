import sqlite3

from app.agents.orchestrator import Orchestrator
from app.domains.cross_domain.goal_agent import GoalAgent
from app.domains.cross_domain.goal_store import GoalStore
from app.domains.router import Domain
from app.proactive.goal_run import GoalCompletionChecker, GoalRunner, GoalRunStore, StopReason
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    """Same ordering convention as tests/test_orchestrator.py's
    ScriptedProvider: per Orchestrator.handle() call, 2 classification
    responses then 1 agent decision response; a completion-check response
    is consumed after each Orchestrator.handle() call by GoalCompletionChecker."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _make_runner(responses: list[str], max_iterations: int = 3) -> tuple[GoalRunner, GoalStore]:
    llm = ScriptedProvider(responses)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    goal_store = GoalStore(conn)
    goal_agent = GoalAgent(goal_store)
    orchestrator = Orchestrator(llm)
    checker = GoalCompletionChecker(llm)
    runner = GoalRunner(orchestrator, goal_agent, goal_store, checker, max_iterations=max_iterations)
    return runner, goal_store


def test_stops_immediately_when_goal_achieved_on_first_try():
    responses = [
        '{"domains": [], "confidence": 0.9}',
        '{"task_type": "research", "confidence": 0.9}',
        '{"action": "final_answer", "answer": "RAG combines retrieval with generation."}',
        '{"achieved": true, "reason": "The answer directly explains RAG as requested."}',
    ]
    runner, goal_store = _make_runner(responses)

    result = runner.run("demo_user", "Explain RAG.", Domain.LEARNING)

    assert result.achieved is True
    assert result.stop_reason == StopReason.ACHIEVED.value
    assert len(result.iterations) == 1

    goal = goal_store.get(result.goal_id)
    assert goal.progress == 1.0


def test_retries_until_achieved_within_budget():
    responses = [
        # iteration 1: not achieved
        '{"domains": [], "confidence": 0.9}',
        '{"task_type": "research", "confidence": 0.9}',
        '{"action": "final_answer", "answer": "A vague first attempt."}',
        '{"achieved": false, "reason": "Too vague, doesn\'t answer the question."}',
        # iteration 2: achieved
        '{"domains": [], "confidence": 0.9}',
        '{"task_type": "research", "confidence": 0.9}',
        '{"action": "final_answer", "answer": "A precise, complete second attempt."}',
        '{"achieved": true, "reason": "This directly and fully answers the question."}',
    ]
    runner, _ = _make_runner(responses, max_iterations=3)

    result = runner.run("demo_user", "Explain RAG.", Domain.LEARNING)

    assert result.achieved is True
    assert len(result.iterations) == 2
    assert result.iterations[0].achieved is False
    assert result.iterations[1].achieved is True


def test_stops_at_max_iterations_when_never_achieved():
    responses = []
    for i in range(3):
        responses += [
            '{"domains": [], "confidence": 0.9}',
            '{"task_type": "research", "confidence": 0.9}',
            f'{{"action": "final_answer", "answer": "attempt {i}"}}',
            '{"achieved": false, "reason": "Still not good enough."}',
        ]
    runner, goal_store = _make_runner(responses, max_iterations=3)

    result = runner.run("demo_user", "Explain RAG.", Domain.LEARNING)

    assert result.achieved is False
    assert result.stop_reason == StopReason.MAX_ITERATIONS_REACHED.value
    assert len(result.iterations) == 3

    goal = goal_store.get(result.goal_id)
    assert goal.status.value == "in_progress"
    assert goal.progress < 1.0


def test_stops_on_no_progress_when_output_repeats():
    responses = [
        '{"domains": [], "confidence": 0.9}',
        '{"task_type": "research", "confidence": 0.9}',
        '{"action": "final_answer", "answer": "same output every time"}',
        '{"achieved": false, "reason": "Not achieved."}',
        '{"domains": [], "confidence": 0.9}',
        '{"task_type": "research", "confidence": 0.9}',
        '{"action": "final_answer", "answer": "same output every time"}',
        '{"achieved": false, "reason": "Still not achieved, identical output."}',
    ]
    runner, _ = _make_runner(responses, max_iterations=5)

    result = runner.run("demo_user", "Explain RAG.", Domain.LEARNING)

    assert result.achieved is False
    assert result.stop_reason == StopReason.NO_PROGRESS_DETECTED.value
    assert len(result.iterations) == 2  # stopped well short of max_iterations=5


def test_creates_a_real_goal_trackable_via_goal_agent():
    responses = [
        '{"domains": [], "confidence": 0.9}',
        '{"task_type": "research", "confidence": 0.9}',
        '{"action": "final_answer", "answer": "done"}',
        '{"achieved": true, "reason": "Complete."}',
    ]
    runner, goal_store = _make_runner(responses)

    result = runner.run("demo_user", "Explain RAG.", Domain.LEARNING)

    goals = goal_store.list_by_owner("demo_user")
    assert any(g.goal_id == result.goal_id for g in goals)


def test_goal_run_store_round_trips_and_lists_by_owner():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = GoalRunStore(conn)

    responses = [
        '{"domains": [], "confidence": 0.9}',
        '{"task_type": "research", "confidence": 0.9}',
        '{"action": "final_answer", "answer": "done"}',
        '{"achieved": true, "reason": "Complete."}',
    ]
    runner, _ = _make_runner(responses)
    result = runner.run("demo_user", "Explain RAG.", Domain.LEARNING)
    store.save(result)

    loaded = store.list_by_owner("demo_user")
    assert len(loaded) == 1
    assert loaded[0].run_id == result.run_id
    assert loaded[0].achieved is True


def test_goal_run_store_is_idempotent_on_resave():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    store = GoalRunStore(conn)

    responses = [
        '{"domains": [], "confidence": 0.9}',
        '{"task_type": "research", "confidence": 0.9}',
        '{"action": "final_answer", "answer": "done"}',
        '{"achieved": true, "reason": "Complete."}',
    ]
    runner, _ = _make_runner(responses)
    result = runner.run("demo_user", "Explain RAG.", Domain.LEARNING)
    store.save(result)
    store.save(result)

    assert len(store.list_by_owner("demo_user")) == 1
