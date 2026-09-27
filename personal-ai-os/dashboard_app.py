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
from app.dashboard_ui.demo_workflow_outputs import CAREER_DEMO, FINANCE_DEMO, PM_DEMO
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
    st.caption(
        "Phase 3, Sections 26-30 · dashboard: Section 51 — the real-time deep-dive below "
        "reads live from GoalStore on every page load (no caching), so it reflects the "
        "actual state after your latest commit, not a fixed snapshot."
    )

    # Real per-goal data from the actual 15 learning-capability goals (GoalStore),
    # NOT the fabricated Kubernetes/Docker demo dict (LEARNING_DEMO) -- that was the
    # bug the user caught: this page previously showed fake concepts, disconnected
    # from the real goals tracked everywhere else on the dashboard.
    real_learning_goals = sorted(
        (g for g in stores["goals"].list_by_owner(USER_ID) if g.domain.value == "LEARNING"),
        key=lambda g: -g.progress,
    )
    real_progress = {g.title: round(g.progress * 10, 1) for g in real_learning_goals}

    dashboard = get_learning_dashboard(stores["goals"], USER_ID, progress=real_progress)

    col1, col2 = st.columns(2)
    col1.metric("Active learning goals", dashboard.learning_goals_count)
    avg_progress = sum(g.progress for g in real_learning_goals) / len(real_learning_goals) if real_learning_goals else 0.0
    col2.metric("Average progress", f"{avg_progress:.0%}")
    st.caption(
        "\"Exercises completed\" is dropped from this page — it was fabricated demo data "
        "(LEARNING_DEMO) with no real store behind it for these capability goals; showing "
        "a number here would be inventing data, not reporting it."
    )

    st.subheader("Real progress per capability (out of 10)")
    st.bar_chart(dashboard.progress)

    st.subheader("Deep dive — what's done, what's left")
    for goal in real_learning_goals:
        criteria = [c for c in goal.success_criteria if not c.startswith("[Progress basis]")]
        basis = next((c[len("[Progress basis] "):] for c in goal.success_criteria if c.startswith("[Progress basis]")), None)
        with st.expander(f"{goal.progress:.0%} — {goal.title}", expanded=False):
            if basis:
                st.caption(f"**Why this score:** {basis}")
            st.markdown("**Success criteria (what 'done' looks like for this capability):**")
            for c in criteria:
                st.write(f"- {c}")


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


_RAG_EXAMPLES_PATH = Path(__file__).resolve().parent / "app" / "dashboard_ui" / "rag_examples.json"


def _load_rag_examples() -> dict | None:
    """Loads app/dashboard_ui/rag_examples.json -- generated by actually
    running scripts/generate_rag_examples.py against the real pipeline
    (real chunking, real embeddings, real FAISS+BM25 hybrid search, real
    cross-encoder reranking, a real Gemini generation call, real
    grounding/citation evaluation), not hand-written."""
    if not _RAG_EXAMPLES_PATH.exists():
        return None
    return json.loads(_RAG_EXAMPLES_PATH.read_text())


def _pca_2d(vectors) -> list[tuple[float, float]]:
    """Plain numpy SVD-based PCA -- no sklearn dependency needed for a
    simple 2D projection of real embedding vectors, purely to visualize
    which chunks land near each other in embedding space."""
    import numpy as np

    X = np.asarray(vectors, dtype="float32")
    if X.shape[0] < 2:
        return [(0.0, 0.0) for _ in range(X.shape[0])]
    centered = X - X.mean(axis=0)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    projected = centered @ vt[:2].T
    return [(float(p[0]), float(p[1])) for p in projected]


def render_rag(stores: dict) -> None:
    st.header("RAG (Retrieval-Augmented Generation)")
    st.caption(
        "Chunking, embedding, and semantic search below are 100% LIVE and interactive -- "
        "paste your own text and query, real results, no LLM call (free, local). "
        "Generation + evaluation further down use pre-generated real examples "
        "(scripts/generate_rag_examples.py) since those need a paid Gemini call, "
        "consistent with this dashboard never making live LLM calls on page render."
    )

    from app.dashboard_ui.rag_diagram import RAG_DIAGRAM

    st.subheader("The RAG journey: input → retrieve → generate → output")
    diagram_id = "rag-mermaid-diagram"
    st.html(
        f"""
        <div id="{diagram_id}" class="mermaid">{RAG_DIAGRAM}</div>
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

    st.divider()
    st.subheader("1. Live chunking + embedding")
    st.caption(
        "Paste any text below. Real chunk_document() splits it, real "
        "SentenceTransformerEmbedding (all-MiniLM-L6-v2) embeds each chunk -- "
        "the 2D plot is a real PCA projection of the real 384-dim vectors, "
        "just for visualizing which chunks land near each other."
    )
    default_text = (
        "Kubernetes is a container orchestration platform. It automates deployment, "
        "scaling, and management of containerized applications. A Kubernetes cluster "
        "consists of a control plane and worker nodes. Pods are the smallest deployable "
        "units, each running one or more containers. Services provide stable networking "
        "for a set of pods. Deployments manage replica sets and rolling updates."
    )
    user_text = st.text_area("Text to chunk and embed", value=default_text, height=120)
    col1, col2 = st.columns(2)
    chunk_size = col1.slider("Chunk size (words)", min_value=10, max_value=100, value=25, step=5)
    overlap = col2.slider("Overlap (words)", min_value=0, max_value=chunk_size - 1, value=5, step=1)

    if user_text.strip():
        from datetime import datetime, timezone

        from app.retrieval.chunking import chunk_document
        from app.retrieval.document import Document
        from app.retrieval.embeddings import SentenceTransformerEmbedding

        now = datetime.now(timezone.utc)
        doc = Document(id="live_doc", text=user_text, source="dashboard", created_at=now, updated_at=now)
        live_chunks = chunk_document(doc, chunk_size=chunk_size, overlap=overlap)

        st.write(f"**{len(live_chunks)} real chunk(s) produced:**")
        for c in live_chunks:
            st.text(f"[{c.id}] ({len(c.text.split())} words): {c.text[:120]}{'...' if len(c.text) > 120 else ''}")

        if len(live_chunks) >= 2:
            with st.spinner("Embedding chunks (real model, runs once, cached)..."):
                embedder = _get_embedder()
                vectors = embedder.embed([c.text for c in live_chunks])
            points = _pca_2d(vectors)
            import pandas as pd

            plot_df = pd.DataFrame(
                {"x": [p[0] for p in points], "y": [p[1] for p in points], "chunk": [c.id for c in live_chunks]}
            )
            st.caption("Real embeddings, real PCA projection to 2D — chunks with similar meaning land closer together:")
            st.scatter_chart(plot_df, x="x", y="y", size=None)
        elif len(live_chunks) == 1:
            st.caption("Need at least 2 chunks to plot a 2D projection.")

    st.divider()
    st.subheader("2. Live semantic search — vector vs keyword vs hybrid")
    st.caption(
        "Real FAISS vector search, real BM25 keyword search, and real reciprocal-rank-fusion "
        "hybrid search — all indexing whatever you typed above."
    )
    query = st.text_input("Search query", value="How does Kubernetes handle networking?")

    if user_text.strip() and query.strip() and len(live_chunks) >= 1:
        from app.retrieval.hybrid_search import reciprocal_rank_fusion
        from app.retrieval.keyword_search import KeywordSearch
        from app.retrieval.vector_search import VectorStore

        with st.spinner("Running real vector + keyword search..."):
            vs = VectorStore(_get_embedder())
            vs.add(live_chunks)
            ks = KeywordSearch()
            ks.add(live_chunks)
            vector_results = vs.search(query, top_k=5)
            keyword_results = ks.search(query, top_k=5)
            fused = reciprocal_rank_fusion([vector_results, keyword_results])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Vector (FAISS, L2 distance)**")
            st.caption("Lower score = more similar")
            for r in vector_results:
                st.text(f"[{r.score:.3f}] {r.chunk.id}\n{r.chunk.text[:80]}")
        with col2:
            st.markdown("**Keyword (BM25)**")
            st.caption("Higher score = more relevant")
            if keyword_results:
                for r in keyword_results:
                    st.text(f"[{r.score:.3f}] {r.chunk.id}\n{r.chunk.text[:80]}")
            else:
                st.caption("No keyword matches (BM25 needs overlapping terms).")
        with col3:
            st.markdown("**Hybrid (reciprocal rank fusion)**")
            st.caption("Merges both rankings — no incompatible score scales")
            for r in fused[:5]:
                st.text(f"[{r.score:.3f}] {r.chunk.id}\n{r.chunk.text[:80]}")

    st.divider()
    st.subheader("3. Full pipeline example: retrieval → generation → evaluation")
    example = _load_rag_examples()
    if example is None:
        st.warning("No RAG example found — run `python scripts/generate_rag_examples.py` first.")
        return

    st.markdown(f"**Question:** {example['question']}")
    with st.expander("Indexed documents (real, synthetic — see scripts/generate_rag_examples.py)", expanded=False):
        for d in example["documents"]:
            st.text(f"[{d['id']}] {d['text']}")

    tab1, tab2, tab3, tab4 = st.tabs(["Retrieval", "Generation + Citations", "Evaluation", "Failure modes"])

    with tab1:
        st.markdown("**Real reranked results (cross-encoder, top candidates after hybrid fusion):**")
        for r in example["reranked_results"]:
            st.text(f"[{r['score']:.3f}] {r['chunk_id']}: {r['text'][:100]}")
        st.warning(
            "**Honest gap, checked directly in specs/personal_rag.md**: hybrid search + "
            "reranking (shown above) are NOT actually wired into `PersonalRagPipeline` "
            "yet — `SecureRetriever` currently wraps plain vector search only. The "
            "generation in the next tab used plain vector retrieval, not these reranked "
            "results. This tab demonstrates hybrid+rerank as real, independently-tested "
            "components (both genuinely run here), not as what production generation "
            "actually uses today."
        )
        st.caption(
            f"Retrieval eval against a human-labeled ground truth "
            f"(relevant_chunk_ids={example['retrieval_ground_truth']}): "
            f"**recall={example['retrieval_metrics']['recall']:.2f}**, "
            f"**precision={example['retrieval_metrics']['precision']:.2f}** "
            f"(computed against the reranked results above)"
        )
        st.caption(
            "Why recall/precision matter: recall tells you if retrieval MISSED something relevant "
            "(bad — the LLM never even sees it); precision tells you how much irrelevant noise got "
            "pulled in (costs context budget, can distract the LLM). Both need a human-labeled "
            "ground truth of what SHOULD have been retrieved — they can't be computed from a live "
            "query alone."
        )

    with tab2:
        st.markdown("**Real generated answer:**")
        st.success(example["final_answer"])
        st.markdown("**Real citations the model produced:**")
        for c in example["citations"]:
            st.text(f"- [{c['chunk_id']}] source={c['source']}")
        if example["memory_used"]:
            st.markdown(f"**Memory used:** {example['memory_used']}")

    with tab3:
        g = example["grounding"]
        col1, col2 = st.columns(2)
        col1.metric("Groundedness score", f"{g['groundedness_score']:.0%}")
        col2.metric("Citation quality", f"{example['citation_quality_score']:.0%}")
        st.caption(
            "**Groundedness** (LLM-as-judge, evaluate_grounding()): what fraction of the answer's "
            "factual claims are actually supported by the retrieved evidence, not the model's general "
            "world knowledge? A hallucinated claim not present in any retrieved chunk lowers this."
        )
        st.markdown(f"Grounded claims: {g['grounded_claim_count']}, unsupported: {g['unsupported_claim_count']}")
        for c in g["citations"]:
            st.text(f"- \"{c['claim'][:80]}...\" -> [{c['chunk_id']}]")
        st.caption(
            "**Citation quality** (deterministic, citation_quality()): does every cited chunk id "
            "actually exist among what was retrieved? A citation to a non-existent or unretrieved "
            "chunk id is a fabricated citation, caught here regardless of whether the claim itself "
            "happens to be true."
        )

    with tab4:
        st.markdown("**Real failure modes in this codebase — what actually happens:**")
        st.markdown(
            "- **Retrieval returns nothing relevant:** `PersonalRagPipeline`'s prompt explicitly "
            "instructs the LLM to say so rather than guess — checked directly in "
            "`app/personal_rag/pipeline.py`'s `ANSWER_PROMPT`."
        )
        st.markdown(
            "- **Generation hallucinates a citation:** caught by `citation_quality()` — a cited "
            "chunk id that was never actually retrieved fails the check, regardless of whether the "
            "claim happens to be true."
        )
        st.markdown(
            "- **Generation makes an ungrounded claim:** caught by `evaluate_grounding()`'s "
            "LLM-as-judge — a claim not supported by any retrieved chunk lowers the groundedness "
            "score, even if no fabricated citation was attached to it."
        )
        st.markdown(
            "- **Context exceeds the token budget:** `ContextBuilder._compress_to_budget()` drops "
            "the lowest-priority sections first (never blindly truncates mid-section) until under "
            "budget — verified by reading the real compression logic."
        )
        st.info(
            "Not fabricated as generic RAG folklore — each of these traces to a specific real "
            "function in this codebase, checked directly rather than assumed."
        )


@st.cache_resource
def _get_embedder():
    from app.retrieval.embeddings import SentenceTransformerEmbedding

    return SentenceTransformerEmbedding()


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
        "RAG": render_rag,
    }
    page = st.sidebar.radio("View", list(pages.keys()))
    st.sidebar.markdown("---")
    st.sidebar.markdown("[Full project README](README.md)")

    pages[page](stores)


if __name__ == "__main__":
    main()
