"""Fully instrumented trace CLI: run a real request through the ONE real
router (UnifiedRouter, via Orchestrator), using the live Gemini API, and
print every stage in detail -- routing decision, tool-call input/output,
memory considered, retrieval, cost, and a trace_id tying it all together.

Not part of the dashboard on purpose (see specs/dashboard_ui.md's non-goals
-- the dashboard never makes live LLM calls). This script is the actual
place to answer "how does the router route, what tool gets called, what's
the input/output, what did it cost" for a real, live query.

HISTORY: this script used to run TWO separate, disconnected routers
(DomainRouter and TaskClassifier+Orchestrator) side by side, because that's
what the codebase actually had -- confirmed by reading the code, not
assumed. The user asked for one combined router instead of two. That's now
app/routing/unified_router.py's UnifiedRouter: classifies domain
(CAREER/PM/FINANCE/LEARNING/GENERAL) and task-type
(RESEARCH/ANALYSIS/PLANNING/UNCLEAR) as two stages of ONE router, and
Orchestrator uses it internally, injecting the classified domain as context
into whichever agent (ResearchAgent/AnalystAgent/PlannerAgent) it dispatches
to. app/main.py and app/api/voice_api.py already use Orchestrator, so this
fix reached production, not just this script.

What this DOES show (all real, all live):
  - trace_id: TraceRecorder's own execution_id for this run
  - The single router's decision: domain (or GENERAL) + task-type, both
    classified by UnifiedRouter
  - Tool-agent decision loop: every real tool call's name, args, and result
    (via Orchestrator's on_tool_call observer hook, forwarded to
    ResearchAgent)
  - Real token counts + real $ cost (via CostTracker, using the per-1K rates
    the user provided for gemini-3.5-flash-lite: $0.00030 input / $0.00250
    output)
  - Real memory considered: naive keyword-overlap matching (NOT semantic
    search -- no vector index over memories exists) against
    PersistentMemoryStore's seeded memories, showing which memories shared
    keywords with the request

What this explicitly does NOT show, because it doesn't exist in this
codebase (checked by reading the actual code, not assumed):
  - Task complexity classification: no such classifier exists anywhere in
    app/. UnifiedRouter classifies domain/task-type only, never a
    complexity tier (easy/medium/hard).
  - Retrieval recall/precision: app/evaluation/retrieval_eval.py's
    evaluate_retrieval() requires a human-labeled ground truth
    (relevant_chunk_ids) per query. No such labels exist for an ad hoc live
    request, so a number here would be fabricated, not measured.

Usage:
    PYTHONPATH=. python scripts/trace_request.py "Should I learn Kubernetes for my career?"

    # Also print the routed domain's golden case counts:
    PYTHONPATH=. python scripts/trace_request.py "..." --with-eval

    # Give the research path something real to retrieve against:
    PYTHONPATH=. python scripts/trace_request.py "What is Kubernetes?" --index-file notes.txt
"""

import argparse
from datetime import datetime, timezone

from app.agents.orchestrator import ClarificationNeeded, Orchestrator
from app.config import require_gemini_key
from app.db.connection import get_connection
from app.domains.router import Domain
from app.evaluation.domain_golden import load_domain_cases
from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.knowledge.secure_retrieval import SecureRetriever
from app.memory.naive_relevance import find_relevant_memories
from app.memory.persistent_store import PersistentMemoryStore
from app.observability.costs import CostRate, CostTracker
from app.observability.trace_store import TraceStore
from app.observability.traces import TraceRecorder
from app.providers.gemini_provider import GeminiProvider
from app.retrieval.chunking import chunk_document
from app.retrieval.document import Document
from app.retrieval.embeddings import SentenceTransformerEmbedding
from app.retrieval.vector_search import VectorStore

DB_PATH = "data/personal_ai.db"
SESSION_ID = "cli_trace"
# Matches scripts/seed_demo_data.py's USER_ID/TENANT_ID exactly, so
# find_relevant_memories() below can actually find the seeded memories
# instead of silently looking under the wrong user/tenant and always
# coming up empty.
USER_ID = "demo_user"
TENANT_ID = "demo_tenant"

# Only tools that are safe to actually invoke live, with no external
# credentials/side effects, are wired in here (calendar/email/github tools
# need real integration credentials this script doesn't assume you have).
# See app/agents/agent_tools.py's build_shared_tools() for exactly which
# tools each agent gets and under what conditions.

DOMAIN_EVAL_DIR = {
    Domain.CAREER: "career",
    Domain.PM: "pm",
    Domain.FINANCE: "finance",
    Domain.LEARNING: "learning",
}

# Rates the user provided for gemini-3.5-flash-lite. If you switch models,
# update this -- CostTracker looks up by exact model name.
GEMINI_RATES = {
    "gemini-3.5-flash-lite": CostRate(input_per_1k=0.00030, output_per_1k=0.00250),
}


def _print_header(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def _build_retrieval_store(index_file: str | None) -> VectorStore | None:
    if not index_file:
        return None
    text = open(index_file).read()
    now = datetime.now(timezone.utc)
    doc = Document(id="cli_index_doc", text=text, source=index_file, created_at=now, updated_at=now)
    chunks = chunk_document(doc, chunk_size=150, overlap=30)
    store = VectorStore(SentenceTransformerEmbedding())
    store.add(chunks)
    return store


def _build_secure_retriever(retrieval_store: VectorStore | None) -> SecureRetriever | None:
    """Wraps the same VectorStore --index-file already builds in a
    SecureRetriever, so the domain-workflow bridge tools (analyze_jd,
    draft_prd -- see app/tools/domain_workflow_tools.py) can use it too,
    not just the plain 'retrieve' tool. One document, owned by this
    script's own USER_ID/TENANT_ID -- consistent with how every other real
    document in this codebase carries ownership metadata (Section 10)."""
    if retrieval_store is None:
        return None
    now = datetime.now(timezone.utc)
    metadata = {
        "cli_index_doc": PersonalDocumentMetadata(
            document_id="cli_index_doc", source="cli", title="Indexed CLI document",
            created_at=now, updated_at=now, category="general",
            sensitivity=Sensitivity.PERSONAL, owner_id=USER_ID, tenant_id=TENANT_ID,
        )
    }
    return SecureRetriever(retrieval_store, metadata)


def trace(text: str, with_eval: bool, index_file: str | None) -> None:
    require_gemini_key()
    recorder = TraceRecorder(session_id=SESSION_ID, user_id=USER_ID)
    trace_id = recorder.trace.execution_id
    # track_usage=True: every real generate() call made through this shared
    # instance appends its actual token usage to llm.usage_log -- no extra
    # LLM calls, just capturing what the SDK already returns.
    llm = GeminiProvider(track_usage=True)
    cost_tracker = CostTracker(journey=f"trace_request:{trace_id}", rates=GEMINI_RATES)
    recorder.trace.model = llm.model_name
    recorder.trace.agent = "trace_request"

    _print_header("TRACE START")
    print(f"trace_id: {trace_id}")
    print(f"Input:    {text}")
    print(f"Model:    {llm.model_name}")

    # ---- Memory considered (naive keyword overlap, NOT semantic search) ----
    _print_header("0. MEMORY CONSIDERED")
    conn = get_connection(DB_PATH)
    memory_store = PersistentMemoryStore(conn)
    with recorder.span("memory_lookup", kind="retrieval", input_text=text) as mem_span:
        relevant_memories = find_relevant_memories(memory_store, TENANT_ID, USER_ID, text)
        mem_span.metadata["memories_considered"] = [
            {"memory_id": m.memory_id, "type": m.type.value, "overlap_words": count}
            for m, count in relevant_memories
        ]
    if relevant_memories:
        print(f"{len(relevant_memories)} memory record(s) shared keywords with this request "
              "(naive keyword overlap, not semantic search -- no vector index over memories exists):")
        for memory, overlap in relevant_memories:
            print(f"  [{memory.memory_id} | {memory.type.value} | overlap={overlap}] {memory.content}")
    else:
        print("No stored memory shared keywords with this request (or none seeded/matching).")
    conn.close()

    # ---- The one router (UnifiedRouter, via Orchestrator) + agent dispatch ----
    _print_header("1. ROUTING + AGENT (UnifiedRouter -> Orchestrator)")

    retrieval_store = _build_retrieval_store(index_file)
    secure_retriever = _build_secure_retriever(retrieval_store)
    if index_file:
        print(f"Indexed {index_file} for 'retrieve', 'analyze_jd', and 'draft_prd' ({len(retrieval_store)} chunks).")
    else:
        print("No --index-file given -- 'retrieve', 'analyze_jd', and 'draft_prd' are not "
              "available this run (each needs an indexed document).")
    print("Always available regardless of --index-file: calculator, analyze_feedback.")

    tool_call_log = []
    classification_holder = {}

    def _on_tool_call(name: str, args: dict, result: str) -> None:
        tool_call_log.append({"name": name, "args": args, "result": result})
        print(f"\n  >> TOOL CALL: {name}")
        print(f"     input:  {args}")
        print(f"     output: {result}")
        with recorder.span(f"tool:{name}", kind="tool", args=args, result=result):
            pass

    def _on_classified(classification) -> None:
        classification_holder["value"] = classification
        with recorder.span("unified_routing", kind="classification", input_text=text) as span:
            span.metadata["domain"] = classification.domain.value if classification.domain else "GENERAL"
            span.metadata["all_domains"] = [d.value for d in classification.all_domains]
            span.metadata["domain_confidence"] = classification.domain_confidence
            span.metadata["task_type"] = classification.task_type.value
            span.metadata["task_confidence"] = classification.task_confidence
        print(f"Domain:        {classification.domain.value if classification.domain else 'GENERAL'} "
              f"(confidence {classification.domain_confidence:.2f})")
        if classification.is_cross_domain:
            print(f"Cross-domain:  {[d.value for d in classification.all_domains]}")
        print(f"Task type:     {classification.task_type.value} (confidence {classification.task_confidence:.2f})")

    orchestrator = Orchestrator(
        llm, retrieval_store=retrieval_store, on_tool_call=_on_tool_call, on_classified=_on_classified,
        secure_retriever=secure_retriever, requester_id=USER_ID, requester_tenant_id=TENANT_ID,
    )

    with recorder.span("orchestrator_run", kind="agent", input_text=text) as orch_span:
        result = orchestrator.handle(text)
        if isinstance(result, ClarificationNeeded):
            print(f"\nClarification: {result.message}")
        else:
            orch_span.metadata["agent"] = result.agent
            orch_span.metadata["output"] = result.output
            orch_span.metadata["stop_reason"] = result.stop_reason
            print(f"\nRouted to:    {result.agent}")
            print(f"Tool calls:   {result.tool_calls or '(none)'}")
            print(f"Stop reason:  {result.stop_reason}")
            print(f"\n--- Orchestrator output ---\n{result.output}")

    registered = ["calculator", "analyze_feedback"]
    if retrieval_store is not None:
        registered += ["retrieve", "analyze_jd", "draft_prd"]
    print(f"\nRegistered tools (this run, all 3 agents): {registered}")

    print(
        "\nTask complexity classification: NOT AVAILABLE -- no complexity "
        "classifier exists anywhere in this codebase (checked app/domains/, "
        "app/agents/, app/routing/, app/evaluation/). UnifiedRouter "
        "classifies domain/task-type only, never a complexity tier."
    )

    # ---- Retrieval evaluation ----
    _print_header("2. RETRIEVAL EVALUATION")
    if tool_call_log and any(c["name"] == "retrieve" for c in tool_call_log):
        print("A real retrieve tool call happened above (see input/output). Recall/precision "
              "specifically are still NOT AVAILABLE for it: app/evaluation/retrieval_eval.py's "
              "evaluate_retrieval() requires a human-labeled ground truth (which chunk ids SHOULD "
              "have been retrieved), which doesn't exist for an ad hoc live request.")
    else:
        print(
            "NOT AVAILABLE for this run -- no retrieve tool call happened (pass --index-file to "
            "give the research agent something to retrieve against). Recall/precision would still "
            "require human-labeled ground truth, which doesn't exist for an ad hoc live request. "
            "See scripts/trace_resume.py for a path that does report real FAISS distance scores "
            "per retrieved chunk."
        )

    # ---- Cost ----
    _print_header("3. COST")
    for i, usage in enumerate(llm.usage_log, start=1):
        cost_tracker.record(
            component=f"llm_call_{i}", model=llm.model_name,
            input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
        )
    journey = cost_tracker.journey
    print(f"Real LLM calls made this run: {len(llm.usage_log)}  "
          "(UnifiedRouter's 2 classification calls + Orchestrator's agent turn(s))")
    for entry in journey.entries:
        print(f"  {entry.component}: input={entry.input_tokens}, output={entry.output_tokens}, cost=${entry.cost:.6f}")
    print(f"\nTotal tokens: input={sum(u.input_tokens for u in llm.usage_log)}, "
          f"output={sum(u.output_tokens for u in llm.usage_log)}")
    print(f"Total cost:   ${journey.total:.6f}  "
          f"(gemini-3.5-flash-lite @ $0.00030/1K in, $0.00250/1K out)")

    recorder.trace.input_tokens = sum(u.input_tokens for u in llm.usage_log)
    recorder.trace.output_tokens = sum(u.output_tokens for u in llm.usage_log)
    recorder.trace.cost = journey.total

    if with_eval and classification_holder.get("value") and classification_holder["value"].domain is not None:
        eval_classification = classification_holder["value"]
        for domain in eval_classification.all_domains:
            eval_dir = DOMAIN_EVAL_DIR.get(domain)
            if not eval_dir:
                continue
            _print_header(f"4. GOLDEN CASES -- {domain.value}")
            cases = load_domain_cases(eval_dir)
            print(f"Golden cases on disk for '{eval_dir}': {len(cases)}")
            for case in cases[:5]:
                print(f"  - [{case.category or 'uncategorized'}] {case.id}")
            if len(cases) > 5:
                print(f"  ... and {len(cases) - 5} more")
            print(
                "\nFull eval/regression suite (per-workflow grading + version-over-version "
                "regression comparison) runs via pytest, not per live request:\n"
                f"    PYTHONPATH=. pytest tests/ -k {eval_dir} -v"
            )

    recorder.finish(status="success")
    _persist_trace(recorder.trace, text)

    _print_header("TRACE END")
    print(f"trace_id: {trace_id}")
    print(f"Saved to {DB_PATH} -- viewable in the dashboard's Traces page.")


def _persist_trace(trace, input_text: str) -> None:
    conn = get_connection(DB_PATH)
    TraceStore(conn).save(trace, input_text=input_text)
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("text", help="The request to route and run, in quotes.")
    parser.add_argument(
        "--with-eval", action="store_true",
        help="Also print the routed domain's golden-case counts (no extra live LLM call -- reuses the router's own classification).",
    )
    parser.add_argument(
        "--index-file", default=None,
        help="Path to a text file to index for the research path's 'retrieve' tool "
             "(real chunking + real embeddings, same as scripts/trace_resume.py).",
    )
    args = parser.parse_args()
    trace(args.text, args.with_eval, args.index_file)


if __name__ == "__main__":
    main()
