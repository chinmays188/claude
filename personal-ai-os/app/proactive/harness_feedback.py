"""Chief of Staff responsibility 4, per the user's own definition:
"COS proactively suggest changes to our workflow (harness) based on every
learning after every run — it gets feeds from our feedback agent, etc."

Checked first, honestly: there is no dedicated "feedback agent" anywhere in
this codebase (app/domains/pm/feedback_intelligence.py's analyze_feedback
is customer-feedback theme clustering — unrelated). Confirmed with the
user: use the REAL signals that already exist rather than build a new
agent from scratch --
  - app/observability/error_analysis.py: real error rate, real
    failures-by-kind, real stop-reason counts, real failure trace_id
    examples, computed from TraceStore.
  - app/dashboard_ui/eval_history.json: a real (if still thin) model/eval
    drift time series, appended by scripts/track_eval_drift.py.
  - app/proactive/goal_run.py's GoalRunStore: real goal-run history — how
    many iterations a goal took, what stop_reason it ended on (achieved /
    max_iterations_reached / no_progress_detected).

This module turns that real data into ONE structured, evidence-grounded
suggestion per call — never a vague "consider improving reliability," and
never invented: every suggestion must cite the actual number(s) that
prompted it (HarnessSuggestion.evidence), and the prompt explicitly
forbids proposing anything the given signals don't support. This is still
a PROPOSAL, never auto-applied -- matching Phase 4's core rule (Section:
Chief of Staff never executes anything itself), just extended to
workflow/prompt/tool changes instead of tool-call plans
(app/proactive/action_plans.py's propose_plan() already covers that case;
this is a distinct, text-only recommendation, not a tool-call plan).
"""

import sqlite3
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.observability.error_analysis import (
    failure_examples,
    span_failure_counts_by_kind,
    stop_reason_counts,
    trace_error_rate,
)
from app.observability.traces import Trace
from app.proactive.goal_run import GoalRun
from app.providers.base import LLMProvider
from app.structured.repair import RepairableGenerator

SUGGESTION_PROMPT = """You are Chief of Staff reviewing real operational signals
from this AI system's own recent runs, to propose ONE concrete workflow or
harness improvement. Base your suggestion ONLY on the evidence given below
— do not invent a problem or number that isn't present in it. If the
evidence doesn't clearly point to a specific improvement, say so honestly
instead of inventing one.

Real evidence from recent runs:
{evidence_block}

Respond with ONLY a JSON object:
{{
  "has_suggestion": true | false,
  "suggestion": "<one concrete, specific workflow/harness change, or empty string if has_suggestion is false>",
  "evidence_cited": "<the specific real number(s) from the evidence above that justify this, or empty string>",
  "reasoning": "<why this change addresses that evidence>"
}}
"""


class HarnessSuggestion(BaseModel):
    """One evidence-grounded proposal. Never auto-applied — a human reviews
    it, same as any other Phase 4 proposal."""

    suggestion_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    owner_id: str
    has_suggestion: bool
    suggestion: str
    evidence_cited: str
    reasoning: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class _RawSuggestion(BaseModel):
    has_suggestion: bool
    suggestion: str = ""
    evidence_cited: str = ""
    reasoning: str = ""


def _build_evidence_block(
    traces: list[Trace], eval_history: list[dict], goal_runs: list[GoalRun],
) -> str:
    """Real numbers only, formatted for the prompt -- every line here is
    traceable back to a real store/file, nothing summarized into a vague
    claim before the LLM even sees it."""
    lines = []

    error_rate = trace_error_rate(traces)
    lines.append(f"- Trace error rate: {error_rate * 100:.1f}% ({len(traces)} traces analyzed)")

    span_counts = span_failure_counts_by_kind(traces)
    if span_counts:
        lines.append(f"- Failed spans by kind: {span_counts}")
    else:
        lines.append("- Failed spans by kind: none recorded")

    stop_reasons = stop_reason_counts(traces)
    if stop_reasons:
        lines.append(f"- Agent-run stop reasons: {stop_reasons}")

    examples = failure_examples(traces, limit_per_kind=1)
    for kind, items in examples.items():
        if items:
            lines.append(f"- Example {kind} failure (trace {items[0]['trace_id']}): {items[0]['error']}")

    if eval_history:
        recent = eval_history[-3:]
        lines.append(f"- Recent eval-drift runs ({len(eval_history)} total, showing last {len(recent)}):")
        for row in recent:
            lines.append(
                f"    recall={row.get('recall')}, precision={row.get('precision')}, "
                f"groundedness={row.get('groundedness_score')}, model={row.get('model')}"
            )
    else:
        lines.append("- Eval-drift history: none recorded yet")

    if goal_runs:
        goal_stop_reasons = {}
        for run in goal_runs:
            goal_stop_reasons[run.stop_reason] = goal_stop_reasons.get(run.stop_reason, 0) + 1
        avg_iterations = sum(len(r.iterations) for r in goal_runs) / len(goal_runs)
        lines.append(
            f"- Goal-run history ({len(goal_runs)} runs): stop reasons {goal_stop_reasons}, "
            f"average iterations per run = {avg_iterations:.1f}"
        )
    else:
        lines.append("- Goal-run history: none recorded yet")

    return "\n".join(lines)


def generate_harness_suggestion(
    llm: LLMProvider, owner_id: str, traces: list[Trace], eval_history: list[dict], goal_runs: list[GoalRun],
) -> HarnessSuggestion:
    evidence_block = _build_evidence_block(traces, eval_history, goal_runs)
    generator = RepairableGenerator(llm, _RawSuggestion)
    raw = generator.generate(SUGGESTION_PROMPT.format(evidence_block=evidence_block))
    return HarnessSuggestion(
        owner_id=owner_id, has_suggestion=raw.has_suggestion, suggestion=raw.suggestion,
        evidence_cited=raw.evidence_cited, reasoning=raw.reasoning,
    )


_SCHEMA = """
CREATE TABLE IF NOT EXISTS harness_suggestions (
    suggestion_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    has_suggestion INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    suggestion_json TEXT NOT NULL
);
"""


class HarnessSuggestionStore:
    """SQLite-backed persistence, same pattern as every other store in this
    project -- so Chief of Staff can show suggestion HISTORY, not just the
    latest call's result."""

    def __init__(self, connection: sqlite3.Connection):
        self._conn = connection
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def save(self, suggestion: HarnessSuggestion) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO harness_suggestions
               (suggestion_id, owner_id, has_suggestion, created_at, suggestion_json)
               VALUES (?, ?, ?, ?, ?)""",
            (
                suggestion.suggestion_id, suggestion.owner_id, int(suggestion.has_suggestion),
                suggestion.created_at.isoformat(), suggestion.model_dump_json(),
            ),
        )
        self._conn.commit()

    def list_by_owner(self, owner_id: str, limit: int = 50) -> list[HarnessSuggestion]:
        rows = self._conn.execute(
            "SELECT suggestion_json FROM harness_suggestions WHERE owner_id = ? ORDER BY created_at DESC LIMIT ?",
            (owner_id, limit),
        ).fetchall()
        return [HarnessSuggestion.model_validate_json(row["suggestion_json"]) for row in rows]
