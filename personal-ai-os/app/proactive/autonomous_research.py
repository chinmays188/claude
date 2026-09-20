from app.agents.research_agent import ResearchAgent
from app.tasks.models import LongRunningTask, TaskState
from app.tasks.store import TaskStore


class AutonomousResearchRunner:
    """Milestone 35: drives a ResearchAgent (Phase 1) through the
    LongRunningTask state machine (Phase 2, Milestone 26), so a research
    request ('Research the top 10 AI PM companies...' — Phase 2's own worked
    example) can be tracked, paused, and resumed like any other long-running
    task, rather than a fire-and-forget synchronous call."""

    def __init__(self, task_store: TaskStore, research_agent: ResearchAgent):
        self._tasks = task_store
        self._agent = research_agent

    def start(self, owner: str, question: str) -> LongRunningTask:
        task = LongRunningTask(owner=owner, description=question)
        self._tasks.create(task)
        self._tasks.transition(task.task_id, TaskState.PLANNING)
        return self._tasks.transition(task.task_id, TaskState.RUNNING)

    def run_to_completion(self, task_id: str) -> LongRunningTask:
        """Runs the agent synchronously and records the result. A real
        deployment would run this on a worker/queue (Phase 5, Milestone 46);
        here it's a direct call, since this sandbox has no queue
        infrastructure to dispatch to."""
        task = self._tasks.get(task_id)
        if task.state != TaskState.RUNNING:
            raise ValueError(f"Task '{task_id}' is not RUNNING (state: {task.state.value}); call start() first.")

        try:
            response = self._agent.run(task.description)
        except Exception as exc:
            return self._tasks.transition(task_id, TaskState.FAILED, result=str(exc))

        self._tasks.transition(task_id, TaskState.EVALUATING, checkpoint={"raw_output": response.output})
        return self._tasks.transition(task_id, TaskState.COMPLETED, result=response.output)
