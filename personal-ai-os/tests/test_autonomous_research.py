import pytest

from app.agents.research_agent import ResearchAgent
from app.db.connection import get_connection
from app.proactive.autonomous_research import AutonomousResearchRunner
from app.providers.base import LLMProvider
from app.tasks.models import TaskState
from app.tasks.store import TaskStore


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def test_start_transitions_task_through_planning_to_running():
    llm = ScriptedProvider([])
    runner = AutonomousResearchRunner(TaskStore(get_connection(":memory:")), ResearchAgent(llm))

    task = runner.start("alice", "Research the top 10 AI PM companies.")

    assert task.state == TaskState.RUNNING


def test_run_to_completion_records_agent_output():
    llm = ScriptedProvider(['{"action": "final_answer", "answer": "Top companies: A, B, C."}'])
    task_store = TaskStore(get_connection(":memory:"))
    runner = AutonomousResearchRunner(task_store, ResearchAgent(llm))
    task = runner.start("alice", "Research the top 10 AI PM companies.")

    completed = runner.run_to_completion(task.task_id)

    assert completed.state == TaskState.COMPLETED
    assert "Top companies" in completed.result


def test_run_to_completion_marks_failed_on_agent_error():
    class BrokenProvider(LLMProvider):
        def generate(self, prompt: str) -> str:
            raise RuntimeError("provider down")

        @property
        def model_name(self) -> str:
            return "broken"

    task_store = TaskStore(get_connection(":memory:"))
    runner = AutonomousResearchRunner(task_store, ResearchAgent(BrokenProvider()))
    task = runner.start("alice", "Research something.")

    failed = runner.run_to_completion(task.task_id)

    assert failed.state == TaskState.FAILED


def test_run_to_completion_requires_running_state():
    llm = ScriptedProvider([])
    task_store = TaskStore(get_connection(":memory:"))
    runner = AutonomousResearchRunner(task_store, ResearchAgent(llm))
    from app.tasks.models import LongRunningTask

    pending_task = LongRunningTask(owner="alice", description="not started via runner")
    task_store.create(pending_task)

    with pytest.raises(ValueError):
        runner.run_to_completion(pending_task.task_id)
