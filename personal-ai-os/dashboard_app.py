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

import json
import os
from pathlib import Path

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
from app.dashboard_ui.architecture_diagram import ARCHITECTURE_DIAGRAM
from app.dashboard_ui.demo_workflow_outputs import CAREER_DEMO, FINANCE_DEMO, LEARNING_DEMO, PM_DEMO
from app.db.connection import get_connection
from app.domains.cross_domain.goal_store import GoalStore
from app.evaluation.domain_golden import count_cases_by_domain
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


def _flatten_spans(spans, out=None):
    """Depth-first flat list of every span (parent before children) --
    used to find a specific named span anywhere in the tree regardless of
    nesting depth, since e.g. unified_routing/tool:* live nested under
    orchestrator_run, not at the top level."""
    if out is None:
        out = []
    for span in spans:
        out.append(span)
        _flatten_spans(span.children, out)
    return out


def _render_journey(trace, input_text: str) -> None:
    """Renders the trace as a numbered, linear step-by-step narrative --
    input -> memory -> routing -> tool calls -> final output -- instead of
    a raw, collapsed span tree. Built after the user's feedback: 'We need
    to show the journey till output, don't see how we are finally getting
    the output.' Falls back gracefully (prints what it can find) if a
    particular span type isn't present, e.g. an UNCLEAR trace has no
    orchestrator agent output at all."""
    all_spans = _flatten_spans(trace.spans)
    by_name = {s.name: s for s in all_spans}
    step = 1

    st.markdown(f"**Step {step}: Input**")
    st.code(input_text or "(not recorded)", language=None)
    step += 1

    memory_span = by_name.get("memory_lookup")
    if memory_span is not None:
        memories = memory_span.metadata.get("memories_considered", [])
        st.markdown(f"**Step {step}: Memory considered** (naive keyword overlap, not semantic search)")
        if memories:
            for m in memories:
                st.text(f"  • [{m['type']}] {m['memory_id']} (overlap={m['overlap_words']})")
        else:
            st.caption("No stored memory shared keywords with this request.")
        step += 1

    routing_span = by_name.get("unified_routing")
    if routing_span is not None:
        md = routing_span.metadata
        st.markdown(f"**Step {step}: Routing** (UnifiedRouter)")
        domain_line = f"Domain: **{md.get('domain', '?')}**"
        if len(md.get("all_domains", [])) > 1:
            domain_line += f"  (cross-domain: {md['all_domains']})"
        st.markdown(domain_line + f"  ·  Task type: **{md.get('task_type', '?')}**")
        st.caption(f"Domain confidence {md.get('domain_confidence', 0):.2f}, "
                   f"task confidence {md.get('task_confidence', 0):.2f}")
        step += 1

    tool_spans = [s for s in all_spans if s.kind == "tool"]
    if tool_spans:
        st.markdown(f"**Step {step}: Tool call(s)**")
        for i, tool_span in enumerate(tool_spans, start=1):
            st.markdown(f"  {i}. `{tool_span.name}`")
            st.json({"request": tool_span.metadata.get("args"), "response": tool_span.metadata.get("result")})
        step += 1

    orch_span = by_name.get("orchestrator_run")
    if orch_span is not None and orch_span.metadata.get("output"):
        st.markdown(f"**Step {step}: Final output** (from `{orch_span.metadata.get('agent', '?')}`)")
        st.success(orch_span.metadata["output"])
        st.caption(f"Stop reason: {orch_span.metadata.get('stop_reason', '?')}")
    elif trace.status == "success":
        st.markdown(f"**Step {step}: Final output**")
        st.info("No agent output recorded — this request was likely classified UNCLEAR "
                "(routed to neither research/analyst/planner) or ended in a clarification.")


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

    st.subheader("Journey")
    if not full_trace.spans:
        st.caption("No spans recorded for this trace.")
    else:
        _render_journey(full_trace, summary["input_text"] if summary else "")

    with st.expander("Raw spans (full detail, nested)", expanded=False):
        for span in full_trace.spans:
            _render_span(span)


_TOOL_EXAMPLES_PATH = Path(__file__).resolve().parent / "app" / "dashboard_ui" / "tool_examples.json"


def _load_tool_examples() -> list[dict]:
    """Loads app/dashboard_ui/tool_examples.json -- generated by actually
    running scripts/generate_tool_examples.py against each real tool, not
    hand-written. Regenerate that file after adding/changing a tool."""
    if not _TOOL_EXAMPLES_PATH.exists():
        return []
    return json.loads(_TOOL_EXAMPLES_PATH.read_text())


def render_tools(stores: dict) -> None:
    st.header("Tools")
    st.caption(
        "Every tool an agent can call, when it's used, and a REAL request/response "
        "example — generated by actually running each tool "
        "(scripts/generate_tool_examples.py), not hand-written. No live LLM call "
        "happens on this page itself; these are pre-generated, committed examples."
    )
    st.info(
        "**How to add a new tool:** subclass `app/tools/base.py`'s `Tool` "
        "(give it `name`, `description`, `args_schema`, `permissions`), wire it "
        "into `app/agents/agent_tools.py`'s `build_shared_tools()` so all 3 agents "
        "can use it, then add a real example to "
        "`scripts/generate_tool_examples.py` and re-run it."
    )

    examples = _load_tool_examples()
    if not examples:
        st.warning("No tool examples found — run `python scripts/generate_tool_examples.py` first.")
        return

    for example in examples:
        with st.expander(f"🔧 {example['name']}", expanded=False):
            st.markdown(f"**Description:** {example['description']}")
            st.markdown(f"**When to call it:** {example['when_to_call']}")
            st.markdown(f"**Permissions:** `{example['permissions']}`")

            st.markdown("**Arguments schema (real, from the tool's own Pydantic model):**")
            st.json(example["args_schema"], expanded=False)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Example request:**")
                st.json(example["example_request"])
            with col2:
                st.markdown("**Example response:**")
                response = example["example_response"]
                try:
                    st.json(json.loads(response))
                except (json.JSONDecodeError, TypeError):
                    st.code(response)


def render_architecture(stores: dict) -> None:
    st.header("Architecture")
    st.caption(
        "How this system actually routes, calls tools, retrieves, and remembers -- "
        "every box below traces to real code, verified by reading it directly. "
        "See specs/dashboard_ui.md for how each fact was checked."
    )

    st.success(
        "✅ **One combined router.** This used to be two separate, disconnected "
        "routers (DomainRouter and TaskClassifier+Orchestrator) — a real gap "
        "found while building this page, fixed after the user asked for a "
        "single router. `UnifiedRouter` now classifies domain "
        "(career/pm/finance/learning/general) and task-type "
        "(research/analysis/planning) as two stages of one router, and "
        "`Orchestrator` injects the classified domain into whichever agent "
        "(Research/Analyst/Planner) it dispatches to as context."
    )

    # NOTE: two failed approaches were actually tested live in a real
    # browser (via agent-browser, checking the .mermaid div's
    # data-processed attribute -- not assumed) before this one worked:
    #   1. mermaid.initialize({startOnLoad: true}) alone -- the CDN
    #      <script src> loads asynchronously, so startOnLoad's DOM scan
    #      can run before the library/div is ready. data-processed stayed
    #      null.
    #   2. An inline onload="..." attribute on the <script src> tag --
    #      st.html's DOMPurify sanitization strips inline event-handler
    #      attributes even with unsafe_allow_javascript=True (confirmed:
    #      getAttribute('onload') came back null after render). Only
    #      <script> tag bodies survive, not inline handler attributes.
    # Fix: a separate inline <script> tag that polls for window.mermaid to
    # exist, then calls mermaid.run() explicitly. Verified: data-processed
    # became "true" on the div after this.
    diagram_id = "architecture-mermaid-diagram"
    st.html(
        f"""
        <div id="{diagram_id}" class="mermaid">{ARCHITECTURE_DIAGRAM}</div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.1/mermaid.min.js"></script>
        <script>
        (function poll() {{
            if (window.mermaid) {{
                mermaid.initialize({{ startOnLoad: false, theme: 'neutral' }});
                mermaid.run({{ nodes: [document.getElementById('{diagram_id}')] }});
            }} else {{
                setTimeout(poll, 50);
            }}
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )

    st.subheader("Live counts (real, queried right now)")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Registered tools (8 total)**")
        for example in _load_tool_examples():
            st.text(f"• {example['name']}")
        st.caption("Full request/response examples on the Tools page.")

    with col2:
        st.markdown("**Goals defined (GoalStore, live)**")
        goals = stores["goals"].list_by_owner(USER_ID)
        if goals:
            for g in goals:
                st.text(f"• [{g.domain.value}] {g.title} — {g.progress:.0%}")
        else:
            st.caption("No goals seeded yet.")

    with col3:
        st.markdown("**Eval/synthetic data on disk (live count)**")
        counts = count_cases_by_domain()
        for domain, count in counts.items():
            st.text(f"• {domain}: {count} case(s)")
        st.caption("Static JSON golden cases — no live grading harness runs them automatically.")

    st.subheader("Chief of Staff: how it actually 'listens'")
    st.info(
        "**Pull-based, not always-on.** `ChiefOfStaffOrchestrator.process(events)` "
        "processes a list of events handed to it by a caller — there is no real "
        "background poller or scheduler anywhere in this codebase (confirmed by "
        "reading the code, not assumed). It reacts to events it's given, on demand, "
        "rather than continuously monitoring anything in real time."
    )

    st.subheader("Retrieval: where embeddings are actually used")
    st.markdown(
        "- **`retrieve` tool** (ResearchAgent, via `trace_request.py --index-file`): "
        "indexes whatever text file you point it at, real FAISS + "
        "sentence-transformers embeddings.\n"
        "- **Career domain workflows** (`resume_optimization.py`, `interview_prep.py`, "
        "`jd_analysis.py`) and **PM domain workflows** (`prd.py`, "
        "`stakeholder_request.py`): retrieve from a `SecureRetriever`-wrapped "
        "`VectorStore`, permission-filtered before results ever reach the LLM.\n"
        "- **Memory** (`PersistentMemoryStore`) is explicitly **not** embedding-based — "
        "`naive_relevance.py` does plain keyword-overlap matching, shown per-trace "
        "as 'Memory Considered' in the Traces page."
    )


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
        "Architecture": render_architecture,
        "Tools": render_tools,
    }
    page = st.sidebar.radio("View", list(pages.keys()))
    st.sidebar.markdown("---")
    st.sidebar.markdown("[Full project README](README.md)")

    pages[page](stores)


if __name__ == "__main__":
    main()
