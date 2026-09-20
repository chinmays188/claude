"""Personal AI OS — Dashboard (portfolio MVP).

Streamlit UI wired directly to the already-tested dashboard data-layer
functions built across Phases 2-4 (app/dashboard/*.py). No new backend logic
lives here — every number shown traces back to a function with its own
pytest coverage; this file only renders it.

Run:
    PYTHONPATH=. streamlit run dashboard_app.py

First run: seed demo data so every page has something to show —
    PYTHONPATH=. python scripts/seed_demo_data.py
"""

import os

import streamlit as st

from app.actions.audit_log import AuditLog
from app.dashboard.chief_of_staff_data import get_chief_of_staff_snapshot
from app.dashboard.data import get_memory_summary, get_todays_activity, get_ai_health
from app.dashboard.domain_data import (
    get_career_dashboard,
    get_finance_dashboard,
    get_learning_dashboard,
    get_pm_dashboard,
)
from app.dashboard_ui.demo_workflow_outputs import CAREER_DEMO, FINANCE_DEMO, LEARNING_DEMO, PM_DEMO
from app.db.connection import get_connection
from app.domains.cross_domain.goal_store import GoalStore
from app.graph.store import GraphStore
from app.memory.persistent_store import PersistentMemoryStore
from app.observability.trace_store import TraceNotFoundError, TraceStore
from app.proactive.commitments import CommitmentStore
from app.proactive.outcome_tracking import OutcomeStore
from app.tasks.store import TaskStore

TENANT_ID = "demo_tenant"
USER_ID = "demo_user"

st.set_page_config(page_title="Personal AI OS", page_icon="🧭", layout="wide")


DB_PATH = "data/personal_ai.db"


@st.cache_resource
def ensure_seeded() -> bool:
    # Streamlit Community Cloud only runs this file -- there's no separate
    # manual step to run scripts/seed_demo_data.py first the way local dev
    # has. Auto-seed on first load if the DB doesn't exist yet, so a fresh
    # deploy isn't just empty pages. Cached so this only runs once per app
    # instance, not once per page load -- but it does NOT cache the
    # connection itself (see get_stores below).
    if not os.path.exists(DB_PATH):
        from scripts.seed_demo_data import seed_all

        conn = get_connection(DB_PATH)
        seed_all(conn)
        conn.close()
    return True


def get_stores():
    # Deliberately NOT @st.cache_resource: sqlite3 connections default to
    # check_same_thread=True, but Streamlit Cloud serves different sessions
    # on different threads, so a single cached connection shared across
    # threads crashed with sqlite3.ProgrammingError in production (caught
    # via a real deployed-app error, not assumed). Opening a fresh
    # connection per script run avoids the threading issue entirely --
    # cheap here since the dashboard only does a handful of small reads.
    ensure_seeded()
    conn = get_connection(DB_PATH)
    return {
        "memory": PersistentMemoryStore(conn),
        "graph": GraphStore(conn),
        "tasks": TaskStore(conn),
        "audit": AuditLog(conn),
        "goals": GoalStore(conn),
        "commitments": CommitmentStore(conn),
        "outcomes": OutcomeStore(conn),
        "traces": TraceStore(conn),
    }


def render_overview(stores: dict) -> None:
    st.header("Overview")
    st.caption("Phase 2, Milestone 29 — Today's Activity / Memory / AI Health")

    today = get_todays_activity([], stores["audit"], stores["tasks"], owner=USER_ID)
    memory = get_memory_summary(stores["memory"], stores["graph"], TENANT_ID, USER_ID)
    health = get_ai_health(groundedness=0.94, tool_success_rate=0.97, retrieval_recall=0.91, regression_passed=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Today's Activity")
        st.metric("Agent runs", today.agent_runs)
        st.metric("Tasks completed", today.tasks_completed)
        st.metric("Pending approvals", today.pending_approvals)

    with col2:
        st.subheader("Memory")
        st.metric("Memories", memory.memories)
        st.metric("Decisions", memory.decisions)
        st.metric("Projects", memory.projects)

    with col3:
        st.subheader("AI Health")
        st.metric("Groundedness", f"{health.groundedness:.0%}")
        st.metric("Tool success rate", f"{health.tool_success_rate:.0%}")
        st.metric("Regression status", health.regression_status)


def render_career(stores: dict) -> None:
    st.header("Career OS")
    st.caption("Phase 3, Sections 6-11 · dashboard: Section 48")

    dashboard = get_career_dashboard(stores["goals"], USER_ID, **CAREER_DEMO)

    col1, col2, col3 = st.columns(3)
    col1.metric("Applications", dashboard.applications)
    col2.metric("Resume readiness", f"{dashboard.resume_readiness:.0%}")
    col3.metric("Interview readiness", f"{dashboard.interview_readiness:.0%}")

    st.metric("Active career goals", dashboard.career_goals_count)
    if dashboard.skill_gaps:
        st.subheader("Skill gaps")
        for gap in dashboard.skill_gaps:
            st.write(f"- {gap}")


def render_pm(stores: dict) -> None:
    st.header("PM OS")
    st.caption("Phase 3, Sections 12-18 · dashboard: Section 49")

    dashboard = get_pm_dashboard(**PM_DEMO)

    col1, col2, col3 = st.columns(3)
    col1.metric("Open requests", dashboard.open_requests)
    col2.metric("Sprint status", dashboard.sprint_status)
    col3.metric("Open commitments", dashboard.commitments_count)

    if dashboard.feedback_themes:
        st.subheader("Feedback themes")
        for theme in dashboard.feedback_themes:
            st.write(f"- {theme}")

    if dashboard.project_risks:
        st.subheader("Project risks")
        for risk in dashboard.project_risks:
            st.warning(risk)


def render_finance(stores: dict) -> None:
    st.header("Finance OS")
    st.caption("Phase 3, Sections 19-25 · dashboard: Section 50 · all numbers computed deterministically, never by an LLM")

    dashboard = get_finance_dashboard(stores["goals"], USER_ID, **FINANCE_DEMO)

    col1, col2 = st.columns(2)
    col1.metric("Portfolio value", f"${dashboard.portfolio_value:,.2f}")
    col2.metric("Finance goals", dashboard.goals_count)

    st.subheader("Allocation")
    st.bar_chart(dashboard.allocation)

    if dashboard.risk_indicators:
        st.subheader("Risk indicators")
        for indicator in dashboard.risk_indicators:
            st.warning(indicator)


def render_learning(stores: dict) -> None:
    st.header("Learning OS")
    st.caption("Phase 3, Sections 26-30 · dashboard: Section 51")

    dashboard = get_learning_dashboard(stores["goals"], USER_ID, **LEARNING_DEMO)

    col1, col2 = st.columns(2)
    col1.metric("Exercises completed", dashboard.exercises_completed)
    col2.metric("Active learning goals", dashboard.learning_goals_count)

    st.subheader("Progress by concept (out of 10)")
    st.bar_chart(dashboard.progress)

    if dashboard.knowledge_gaps:
        st.subheader("Knowledge gaps")
        for gap in dashboard.knowledge_gaps:
            st.write(f"- {gap}")


def render_chief_of_staff(stores: dict) -> None:
    st.header("Chief of Staff")
    st.caption("Phase 4, Milestone 43")

    snapshot = get_chief_of_staff_snapshot(stores["commitments"], stores["outcomes"], USER_ID)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Open commitments", snapshot.open_commitments)
    col2.metric("Overdue", snapshot.overdue_commitments, delta_color="inverse")
    col3.metric("Pending outcomes", snapshot.pending_outcomes)
    success_rate_display = f"{snapshot.outcome_success_rate:.0%}" if snapshot.outcome_success_rate is not None else "—"
    col4.metric("Outcome success rate", success_rate_display)


def _render_span(span, indent: int = 0) -> None:
    prefix = "  " * indent + "└─ " if indent else ""
    duration = f"{span.duration_ms:.0f}ms" if span.duration_ms is not None else "?"
    status_icon = "✅" if span.status == "success" else "❌"
    st.text(f"{prefix}{status_icon} [{span.kind}] {span.name}  ({duration})")
    if span.metadata:
        st.json(span.metadata, expanded=False)
    if span.error:
        st.error(span.error)
    for child in span.children:
        _render_span(child, indent=indent + 1)


def render_traces(stores: dict) -> None:
    st.header("Traces")
    st.caption(
        "Real, live trace_ids saved by scripts/trace_request.py (not the dashboard itself — "
        "this page is read-only, no live LLM calls happen here). Run a request via that "
        "script, then find it here by trace_id."
    )

    trace_store = stores["traces"]
    summaries = trace_store.list_summaries(limit=200)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Trace IDs")
    if not summaries:
        st.sidebar.caption("No traces saved yet — run scripts/trace_request.py first.")
        selected_id = None
    else:
        options = {
            f"{s['execution_id'][:8]}… · {s['status']} · {s['created_at'][:19]}": s["execution_id"]
            for s in summaries
        }
        chosen_label = st.sidebar.radio("Newest first", list(options.keys()), key="trace_sidebar_pick")
        selected_id = options[chosen_label]

    search_id = st.text_input(
        "Or paste a trace_id directly",
        value=selected_id or "",
        help="Full trace_id (execution_id) as printed by scripts/trace_request.py.",
    )

    if not search_id:
        if summaries:
            st.info("Select a trace from the sidebar, or paste a trace_id above.")
        return

    try:
        full_trace = trace_store.get(search_id)
    except TraceNotFoundError:
        st.error(f"No trace found for trace_id: {search_id}")
        return

    summary = next((s for s in summaries if s["execution_id"] == search_id), None)

    st.subheader(f"Trace: {full_trace.execution_id}")
    if summary:
        st.caption(f"Input: {summary['input_text']}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Status", full_trace.status)
    col2.metric("Latency", f"{full_trace.latency_ms:.0f} ms")
    col3.metric("Tool calls", full_trace.tool_calls)
    col4.metric("Cost", f"${full_trace.cost:.6f}")

    col5, col6 = st.columns(2)
    col5.metric("Input tokens", full_trace.input_tokens)
    col6.metric("Output tokens", full_trace.output_tokens)

    st.markdown(f"**Model:** {full_trace.model}  ·  **Agent:** {full_trace.agent}")

    st.subheader("Spans")
    if not full_trace.spans:
        st.caption("No spans recorded for this trace.")
    for span in full_trace.spans:
        _render_span(span)


def main() -> None:
    st.title("🧭 Personal AI OS")
    st.caption(
        "A voice-first personal AI operating system, built as a 5-phase, "
        "60-milestone AI engineering learning lab. All data below is "
        "fabricated demo data — see scripts/seed_demo_data.py."
    )

    stores = get_stores()

    pages = {
        "Overview": render_overview,
        "Career": render_career,
        "PM": render_pm,
        "Finance": render_finance,
        "Learning": render_learning,
        "Chief of Staff": render_chief_of_staff,
        "Traces": render_traces,
    }
    page = st.sidebar.radio("View", list(pages.keys()))
    st.sidebar.markdown("---")
    st.sidebar.markdown("[Full project README](README.md)")

    pages[page](stores)


if __name__ == "__main__":
    main()
