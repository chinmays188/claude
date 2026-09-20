from app.platform.queue import Job, JobQueue
from app.tasks.models import LongRunningTask, TaskState
from app.tasks.store import TaskStore


class WorkflowHandler:
    """A callable that actually does the work for one workflow job payload,
    returning a text result or raising on failure. Callers register one per
    workflow type (e.g. 'autonomous_research', 'weekly_review')."""

    def run(self, payload: dict) -> str:
        raise NotImplementedError


class WorkflowRuntime:
    """Milestone 47: 'Persistent Workflow Runtime.' Ties JobQueue (Milestone
    46) to Phase 2's LongRunningTask state machine — a queued job is a unit
    of dispatch, the LongRunningTask is the durable, resumable record of a
    workflow's progress. This is the production-shaped version of Phase 4's
    AutonomousResearchRunner: instead of calling the agent synchronously in
    the caller's own process, work is enqueued and a worker (process_one)
    picks it up, matching Section (Phase 5) 46-47's queue+worker split."""

    def __init__(self, job_queue: JobQueue, task_store: TaskStore, handlers: dict[str, WorkflowHandler]):
        self._queue = job_queue
        self._tasks = task_store
        self._handlers = handlers

    def submit(self, owner: str, workflow_type: str, payload: dict) -> LongRunningTask:
        if workflow_type not in self._handlers:
            raise ValueError(f"No handler registered for workflow type '{workflow_type}'.")

        task = LongRunningTask(owner=owner, description=f"{workflow_type}: {payload}")
        self._tasks.create(task)

        self._queue.enqueue("workflows", {"workflow_type": workflow_type, "task_id": task.task_id, "payload": payload})
        return task

    def process_one(self, queue_name: str = "workflows") -> Job | None:
        """Milestone 47: a worker's main loop body — claim one job, run its
        handler, update the corresponding LongRunningTask, and record success
        or failure on the queue (which handles retry/dead-letter itself,
        Milestone 46). Returns None if nothing was queued."""
        job = self._queue.dequeue(queue_name)
        if job is None:
            return None

        task_id = job.payload["task_id"]
        workflow_type = job.payload["workflow_type"]
        handler = self._handlers[workflow_type]

        self._tasks.transition(task_id, TaskState.PLANNING)
        self._tasks.transition(task_id, TaskState.RUNNING)

        try:
            result = handler.run(job.payload["payload"])
        except Exception as exc:
            self._tasks.transition(task_id, TaskState.FAILED, result=str(exc))
            self._queue.fail(job.job_id, str(exc))
            return job

        self._tasks.transition(task_id, TaskState.EVALUATING)
        self._tasks.transition(task_id, TaskState.COMPLETED, result=result)
        self._queue.complete(job.job_id)
        return job
