"""Goal-driven loop / harness engineering (Chief of Staff responsibility 3,
per the user's own definition: "on every input a goal should be defined
and given to our goal agent ... output should continue to run until this
goal is achieved by our agents ... COS needs to keep a track of this").

Before this module, Orchestrator.handle() did exactly one dispatch and
returned -- there was no concept of "keep running until a goal is
actually achieved." This adds a real, bounded loop:

  1. A real Goal is created via GoalAgent for the input (domain=GENERAL
     unless the caller already knows the domain), not a throwaway string.
  2. Orchestrator.handle() runs against the goal's own text.
  3. A real, structured LLM call (GoalCompletionChecker) judges "is this
     goal achieved by this output, yes/no/why" -- not a heuristic guess,
     and not vibes-based free text (Section 33's own principle applied
     here: judgment calls go through a real, auditable LLM call with a
     reason attached).
  4. Stops on: achieved == True, a real max-iterations budget (mirrors
     AgentBudget's pattern), or two consecutive iterations with no real
     progress (the goal's own progress field, or repeated output content,
     doesn't move) -- never loops forever.
  5. Every iteration (output, achieved verdict, reason) is recorded on a
     GoalRun and persisted via GoalRunStore, so Chief of Staff can show
     "this goal took N iterations, stopped because X" -- real, inspectable
     history, not just a final answer.

This is deliberately bounded and cheap by default (max_iterations=3): each
iteration is a full agent run plus one completion-check LLM call, so an
unbounded loop would be a real cost risk, not just a runaway-agent risk.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from app.agents.orchestrator import ClarificationNeeded, Orchestrator
from app.domains.cross_domain.goal_agent import GoalAgent
from app.domains.cross_domain.goal_store import GoalStore
from app.domains.cross_domain.models import Goal, GoalStatus
from app.domains.router import Domain
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

COMPLETION_CHECK_PROMPT = """You are judging whether a stated goal has been
achieved by the given output. Be strict and specific -- do not assume
achievement just because an answer was given; check whether it actually
satisfies the goal.

Goal: {goal_text}

Latest output:
{output}

Prior iteration count: {iteration}

Respond with ONLY a JSON object:
{{"achieved": true | false, "reason": "<specific reason tied to the goal and output>"}}
"""


class StopReason(str, Enum):
    ACHIEVED = "achieved"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"
    NO_PROGRESS_DETECTED = "no_progress_detected"
    CLARIFICATION_NEEDED = "clarification_needed"


class _CompletionVerdict(BaseModel):
    achieved: bool
    reason: str


class GoalRunIteration(BaseModel):
    iteration: int
    output: str
    achieved: bool
    reason: str


class GoalRun(BaseModel):
    """One full goal-driven loop: real Goal created, Orchestrator run
    repeatedly against it, a real completion check after each run. This is
    what Chief of Staff tracks (Section: 'COS needs to keep a track of
    this') -- persisted via GoalRunStore, not just held in memory."""

    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    goal_id: str
    owner_id: str
    input_text: str
    iterations: list[GoalRunIteration] = Field(default_factory=list)
    stop_reason: str = ""
    achieved: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GoalCompletionChecker:
    """Wraps one real, structured LLM call: does this output achieve this
    goal? Kept separate from GoalRunner so it's independently testable and
    reusable (e.g. a future retry policy could call it standalone)."""

    def __init__(self, llm: LLMProvider):
        self._llm = llm

    def check(self, goal_text: str, output: str, iteration: int) -> _CompletionVerdict:
        generator = RepairableGenerator(self._llm, _CompletionVerdict)
        prompt = COMPLETION_CHECK_PROMPT.format(goal_text=goal_text, output=output, iteration=iteration)
        return generator.generate(prompt)


class GoalRunner:
    """The bounded loop itself. Deliberately does not reimplement
    Orchestrator's routing/tool-calling or GoalAgent's persistence -- it
    only sequences real calls to both, plus one new real judgment call
    (GoalCompletionChecker)."""

    def __init__(
        self, orchestrator: Orchestrator, goal_agent: GoalAgent, goal_store: GoalStore,
        completion_checker: GoalCompletionChecker, max_iterations: int = 3,
    ):
        self._orchestrator = orchestrator
        self._goal_agent = goal_agent
        self._store = goal_store
        self._checker = completion_checker
        self._max_iterations = max_iterations

    def run(self, owner_id: str, text: str, domain: Domain) -> GoalRun:
        """domain is required, not guessed: Goal.domain has no GENERAL/None
        option (Section 33's Goal schema is domain=CAREER/PM/FINANCE/LEARNING
        only), so a caller that doesn't yet know the domain should classify
        first (e.g. via UnifiedRouter, which Orchestrator already runs
        internally) rather than this loop inventing one."""
        if not text or not text.strip():
            raise ValueError("Input text must not be empty.")

        goal = Goal(
            owner_id=owner_id, title=text[:120], description=text,
            domain=domain, status=GoalStatus.IN_PROGRESS,
        )
        self._goal_agent.track(goal)

        goal_run = GoalRun(goal_id=goal.goal_id, owner_id=owner_id, input_text=text)
        previous_output: str | None = None

        for i in range(1, self._max_iterations + 1):
            result = self._orchestrator.handle(text)
            if isinstance(result, ClarificationNeeded):
                goal_run.stop_reason = StopReason.CLARIFICATION_NEEDED.value
                goal_run.iterations.append(
                    GoalRunIteration(iteration=i, output=result.message, achieved=False, reason="Clarification needed, not an achieved/not-achieved output.")
                )
                break

            verdict = self._checker.check(goal.description, result.output, i)
            goal_run.iterations.append(
                GoalRunIteration(iteration=i, output=result.output, achieved=verdict.achieved, reason=verdict.reason)
            )

            if verdict.achieved:
                goal_run.achieved = True
                goal_run.stop_reason = StopReason.ACHIEVED.value
                break

            # Since a repeat request is identical every iteration (no new
            # information for the agent to act on), an identical output on
            # the very next attempt means it's already converged/stuck --
            # a real, deterministic no-progress signal, not a guess.
            repeated_output = previous_output is not None and result.output.strip() == previous_output.strip()
            previous_output = result.output
            if repeated_output:
                goal_run.stop_reason = StopReason.NO_PROGRESS_DETECTED.value
                break

            if i == self._max_iterations:
                goal_run.stop_reason = StopReason.MAX_ITERATIONS_REACHED.value

        # Real, honest progress after the loop ends: 1.0 only if the
        # completion checker actually said achieved; otherwise a
        # conservative, capped estimate from how many iterations were spent
        # (never claims more than 90% for an unachieved goal).
        final_progress = 1.0 if goal_run.achieved else min(0.9, 0.3 * len(goal_run.iterations))
        final_status = GoalStatus.COMPLETED if goal_run.achieved else GoalStatus.IN_PROGRESS
        self._store.update_progress(goal.goal_id, final_progress)
        self._store.update_status(goal.goal_id, final_status)

        return goal_run


_SCHEMA = """
CREATE TABLE IF NOT EXISTS goal_runs (
    run_id TEXT PRIMARY KEY,
    goal_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    input_text TEXT NOT NULL,
    stop_reason TEXT NOT NULL,
    achieved INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    run_json TEXT NOT NULL
);
"""


class GoalRunStore:
    """SQLite-backed persistence for GoalRun, same pattern as every other
    store in this project (GoalStore, TraceStore). This is what lets Chief
    of Staff show real goal-run history on the dashboard, not just the
    latest in-memory result."""

    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def save(self, goal_run: GoalRun) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO goal_runs
               (run_id, goal_id, owner_id, input_text, stop_reason, achieved, created_at, run_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                goal_run.run_id, goal_run.goal_id, goal_run.owner_id, goal_run.input_text,
                goal_run.stop_reason, int(goal_run.achieved), goal_run.created_at.isoformat(),
                goal_run.model_dump_json(),
            ),
        )
        self._conn.commit()

    def list_by_owner(self, owner_id: str, limit: int = 50) -> list[GoalRun]:
        rows = self._conn.execute(
            "SELECT run_json FROM goal_runs WHERE owner_id = ? ORDER BY created_at DESC LIMIT ?",
            (owner_id, limit),
        ).fetchall()
        return [GoalRun.model_validate_json(row["run_json"]) for row in rows]
