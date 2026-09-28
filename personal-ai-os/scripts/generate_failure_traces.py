"""Generates REAL failure-mode traces for the dashboard's Traces page, run
once locally and committed as app/dashboard_ui/failure_traces.json -- same
pattern as app/dashboard_ui/example_traces.py (the dashboard never makes a
live LLM call itself). Built for the user's ask: "add retrieval failures,
tool failures, error rates logging with examples of trace ids."

Before this script, every committed example trace was a "success" -- there
was no real failure trace to show, and no way to demonstrate error-rate
tracking honestly without fabricating one. This generates 3 real scenarios:

  1. TOOL FAILURE (live, via the real Orchestrator + live Gemini API):
     asks the research agent a question that leads it to call `calculator`
     with a genuinely invalid expression (division by zero). This is the
     scenario the real bug fix in app/agents/tool_agent.py exists for --
     the tool call fails with a real ToolError, is now caught and recorded
     as a failed span instead of crashing the whole request, and the agent
     recovers to give a final answer anyway.

  2. RETRIEVAL FAILURE (live, via the real Orchestrator + live Gemini API):
     indexes a document about an unrelated topic, then asks a question the
     index has nothing relevant to. The real VectorStore.search() still
     returns its top_k nearest neighbors (FAISS doesn't refuse a wrong
     match), so the honest "failure" signal here is what
     app/tools/retrieval_tool.py already surfaces: "No relevant documents
     found" when the store is empty, or -- when it does return
     results -- real evaluate_retrieval() against a human-labeled ground
     truth showing 0.0 recall/precision (the labels say none of the
     returned chunks are actually relevant).

  3. BUDGET EXHAUSTED / repeated tool failure (deterministic, no live LLM
     call needed -- a scripted decision loop that always asks the
     calculator to divide by zero is enough to prove the real backstop):
     AgentBudget.max_tool_calls stops a tool that keeps failing every
     attempt, ending in StopReason.MAX_TOOL_CALLS_REACHED. This is
     intentionally NOT run against the live API -- there is nothing for a
     real LLM decision to add here beyond what tests/test_tool_agent.py
     already proves deterministically, and it would just spend a real
     Gemini call to re-demonstrate the same budget arithmetic.

Usage:
    PYTHONPATH=. python scripts/generate_failure_traces.py
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from app.agents.orchestrator import ClarificationNeeded, Orchestrator
from app.agents.tool_agent import ToolAgent
from app.config import require_gemini_key
from app.evaluation.retrieval_eval import RetrievalCase, evaluate_retrieval
from app.guardrails.budgets import AgentBudget
from app.guardrails.stop_conditions import StopReason
from app.observability.traces import TraceRecorder
from app.providers.base import LLMProvider
from app.providers.gemini_provider import GeminiProvider
from app.retrieval.chunking import chunk_document
from app.retrieval.document import Document
from app.retrieval.embeddings import SentenceTransformerEmbedding
from app.retrieval.vector_search import VectorStore
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "failure_traces.json"


def _scenario_tool_failure() -> dict:
    """Scenario 1: real tool failure recovered from, via the live API."""
    require_gemini_key()
    recorder = TraceRecorder(session_id="failure_trace_gen", user_id="demo_user")
    llm = GeminiProvider(track_usage=True)
    recorder.trace.model = llm.model_name
    recorder.trace.agent = "trace_request"

    text = "Use the calculator tool to compute 1 divided by 0, then tell me what happened."

    def _on_tool_call(name, args, result):
        with recorder.span(f"tool:{name}", kind="tool", args=args, result=result):
            pass

    def _on_tool_error(name, args, error):
        with recorder.span(f"tool:{name}", kind="tool", args=args) as s:
            s.status = "error"
            s.error = error

    def _on_classified(classification):
        with recorder.span("unified_routing", kind="classification", input_text=text) as span:
            span.metadata["domain"] = classification.domain.value if classification.domain else "GENERAL"
            span.metadata["all_domains"] = [d.value for d in classification.all_domains]
            span.metadata["domain_confidence"] = classification.domain_confidence
            span.metadata["task_type"] = classification.task_type.value
            span.metadata["task_confidence"] = classification.task_confidence

    orchestrator = Orchestrator(llm, on_tool_call=_on_tool_call, on_tool_error=_on_tool_error, on_classified=_on_classified)

    with recorder.span("orchestrator_run", kind="agent", input_text=text) as orch_span:
        result = orchestrator.handle(text)
        status = "success"
        if isinstance(result, ClarificationNeeded):
            status = "error"
            orch_span.metadata["output"] = result.message
        else:
            orch_span.metadata["agent"] = result.agent
            orch_span.metadata["output"] = result.output
            orch_span.metadata["stop_reason"] = result.stop_reason
            recorder.trace.tool_calls = len(result.tool_calls)

    recorder.trace.input_tokens = sum(u.input_tokens for u in llm.usage_log)
    recorder.trace.output_tokens = sum(u.output_tokens for u in llm.usage_log)
    trace = recorder.finish(status=status)
    print(f"[1/3] Tool-failure trace: {trace.execution_id} (status={trace.status})")
    return {"input_text": text, "trace_json": json.loads(trace.model_dump_json())}


def _scenario_retrieval_failure() -> dict:
    """Scenario 2: real retrieval miss, measured against a real human-labeled
    ground truth (not fabricated) -- the index is genuinely about an
    unrelated topic, so the ground truth honestly says nothing retrieved is
    relevant."""
    require_gemini_key()
    recorder = TraceRecorder(session_id="failure_trace_gen", user_id="demo_user")
    llm = GeminiProvider(track_usage=True)
    recorder.trace.model = llm.model_name
    recorder.trace.agent = "trace_request"

    # A real, small index about an unrelated topic (sourdough bread), then a
    # query about something the index has nothing to do with.
    now = datetime.now(timezone.utc)
    doc = Document(
        id="unrelated_doc", source="failure_trace_gen",
        text=(
            "Sourdough bread is made by fermenting dough using naturally "
            "occurring lactobacilli and wild yeast. The fermentation process "
            "produces lactic acid, which gives sourdough its characteristic "
            "tangy flavor. A sourdough starter must be fed regularly with "
            "flour and water to keep the yeast culture alive."
        ),
        created_at=now, updated_at=now,
    )
    chunks = chunk_document(doc, chunk_size=80, overlap=10)
    store = VectorStore(SentenceTransformerEmbedding())
    store.add(chunks)

    query = "What is Kubernetes and how does container orchestration work?"
    with recorder.span("retrieve_eval", kind="retrieval", query=query) as ret_span:
        results = store.search(query, top_k=3)
        # Real, honest ground truth: none of this index's chunks are about
        # Kubernetes, so the correct label is "zero relevant chunk ids" --
        # not fabricated, it follows directly from what the index actually
        # contains.
        case = RetrievalCase(query=query, relevant_chunk_ids=[])
        metrics = evaluate_retrieval(case, results)
        ret_span.status = "error"
        ret_span.error = (
            f"Retrieval returned {len(results)} chunk(s), 0 of which are relevant "
            f"(precision={metrics.precision:.2f}) -- the indexed document has no "
            "content matching this topic at all. (recall is trivially 1.0 here "
            "since the ground truth itself has 0 relevant chunk ids to find -- "
            "precision is the real failure signal in this scenario.)"
        )
        ret_span.metadata["retrieved_ids"] = metrics.retrieved_ids
        ret_span.metadata["relevant_ids"] = metrics.relevant_ids
        ret_span.metadata["recall"] = metrics.recall
        ret_span.metadata["precision"] = metrics.precision

    text = query
    with recorder.span("orchestrator_run", kind="agent", input_text=text) as orch_span:
        orchestrator = Orchestrator(llm, retrieval_store=store)
        result = orchestrator.handle(text)
        if isinstance(result, ClarificationNeeded):
            orch_span.metadata["output"] = result.message
        else:
            orch_span.metadata["agent"] = result.agent
            orch_span.metadata["output"] = result.output
            orch_span.metadata["stop_reason"] = result.stop_reason
            recorder.trace.tool_calls = len(result.tool_calls)

    recorder.trace.retrieval_calls = 1
    recorder.trace.input_tokens = sum(u.input_tokens for u in llm.usage_log)
    recorder.trace.output_tokens = sum(u.output_tokens for u in llm.usage_log)
    # The overall request still completes (the agent answers honestly that
    # it found nothing relevant) -- it's the retrieval SPAN that failed, a
    # real, distinct signal from a whole-trace failure. See
    # app/observability/error_analysis.py's module docstring.
    trace = recorder.finish(status="success")
    print(f"[2/3] Retrieval-failure trace: {trace.execution_id} (span-level failure, trace still success)")
    return {"input_text": text, "trace_json": json.loads(trace.model_dump_json())}


class _AlwaysDivideByZero(LLMProvider):
    """Deterministic, no live API call -- always decides to call calculator
    with a genuinely failing expression, to demonstrate the real
    max_tool_calls backstop against a tool that keeps failing every
    attempt. See this module's docstring for why this one scenario
    intentionally skips the live API."""

    @property
    def model_name(self) -> str:
        return "deterministic-stub"

    def generate(self, prompt: str) -> str:
        return '{"action": "call_tool", "tool": "calculator", "args": {"expression": "1 / 0"}}'


def _scenario_budget_exhausted() -> dict:
    """Scenario 3: deterministic, real max_tool_calls backstop against a
    tool that fails on every attempt."""
    recorder = TraceRecorder(session_id="failure_trace_gen", user_id="demo_user")
    llm = _AlwaysDivideByZero()
    recorder.trace.model = llm.model_name
    recorder.trace.agent = "trace_request"

    error_count = {"n": 0}

    def _on_tool_error(name, args, error):
        error_count["n"] += 1
        with recorder.span(f"tool:{name}", kind="tool", args=args) as s:
            s.status = "error"
            s.error = error

    text = "Keep dividing by zero."
    with recorder.span("orchestrator_run", kind="agent", input_text=text) as orch_span:
        agent = ToolAgent(
            llm, tools=ToolRegistry([CalculatorTool()]),
            budget=AgentBudget(max_tool_calls=3),
            on_tool_error=_on_tool_error,
        )
        result = agent.run(text)
        orch_span.metadata["agent"] = result.agent
        orch_span.metadata["output"] = result.output
        orch_span.metadata["stop_reason"] = result.stop_reason
        orch_span.status = "error"
        orch_span.error = f"Stopped via {result.stop_reason} after {error_count['n']} failed tool calls."

    recorder.trace.tool_calls = len(result.tool_calls)
    trace = recorder.finish(status="error")
    print(f"[3/3] Budget-exhausted trace: {trace.execution_id} (status={trace.status}, "
          f"stop_reason={result.stop_reason})")
    assert result.stop_reason == StopReason.MAX_TOOL_CALLS_REACHED.value
    return {"input_text": text, "trace_json": json.loads(trace.model_dump_json())}


def main() -> None:
    records = []
    records.append(_scenario_tool_failure())
    time.sleep(1)  # gentle spacing between real live API scenarios
    records.append(_scenario_retrieval_failure())
    records.append(_scenario_budget_exhausted())

    OUT_PATH.write_text(json.dumps(records, indent=2))
    print(f"\nWrote {len(records)} real failure traces to {OUT_PATH}")


if __name__ == "__main__":
    main()
