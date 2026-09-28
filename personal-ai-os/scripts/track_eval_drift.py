"""Tracks real model/pipeline drift over time for the dashboard's Traces
page, per the user's ask: "track model drifting signals overtime."

Reuses the exact same real fixture scripts/generate_rag_examples.py already
built and committed (real synthetic achievement documents, a real question,
a real human-labeled retrieval ground truth) -- not a new, separate
fixture -- so every run of this script is directly comparable to every
other run: same documents, same question, same ground truth, only the
model/pipeline code and the live API's actual behavior can differ between
runs.

Each run re-executes the REAL retrieval + generation + evaluation pipeline
(real embeddings, real hybrid search + rerank, a real live Gemini call, real
grounding/citation-quality evaluation) and appends one real, timestamped
row to app/dashboard_ui/eval_history.json:
    {"timestamp": ..., "model": ..., "recall": ..., "precision": ...,
     "groundedness_score": ..., "citation_quality_score": ..., "latency_ms": ...}

This is a real time series, not a simulated one -- it starts thin (as few
as 1 point) and only grows meaningfully once run repeatedly over time
(e.g. before/after a model or prompt change, or on a periodic cadence).
The dashboard must disclose when there isn't enough history yet to call
something a "trend" (fewer than 3 points), not imply drift that hasn't
actually been observed.

Usage:
    PYTHONPATH=. python scripts/track_eval_drift.py
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from app.config import require_gemini_key
from app.evaluation.grounding_eval import citation_quality, evaluate_grounding
from app.evaluation.retrieval_eval import evaluate_retrieval
from app.knowledge.secure_retrieval import SecureRetriever
from app.memory.models import MemoryRecord, MemoryType
from app.memory.retrieval import MemoryRetriever
from app.personal_rag.pipeline import PersonalRagPipeline
from app.providers.gemini_provider import GeminiProvider
from app.retrieval.embeddings import SentenceTransformerEmbedding
from app.retrieval.hybrid_search import reciprocal_rank_fusion
from app.retrieval.keyword_search import KeywordSearch
from app.retrieval.reranker import CrossEncoderReranker
from scripts.generate_rag_examples import (
    NOW,
    QUESTION,
    REQUESTER_ID,
    RETRIEVAL_GROUND_TRUTH,
    TENANT_ID,
    build_stores,
)

HISTORY_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "eval_history.json"


def _load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    return json.loads(HISTORY_PATH.read_text())


def run_once() -> dict:
    require_gemini_key()
    llm = GeminiProvider()
    start = time.monotonic()

    vector_store, keyword_store, all_chunks, metadata = build_stores()
    secure_retriever = SecureRetriever(vector_store, metadata)

    vector_results = vector_store.search(QUESTION, top_k=10)
    keyword_results = keyword_store.search(QUESTION, top_k=10)
    fused = reciprocal_rank_fusion([vector_results, keyword_results])
    reranker = CrossEncoderReranker()
    reranked = reranker.rerank(QUESTION, fused, top_k=5)
    retrieval_metrics = evaluate_retrieval(RETRIEVAL_GROUND_TRUTH, reranked)

    embedding_model = SentenceTransformerEmbedding()
    memory_retriever = MemoryRetriever(embedding_model)
    memory_candidates = [
        MemoryRecord(
            memory_id="mem1", tenant_id=TENANT_ID, user_id=REQUESTER_ID, type=MemoryType.PREFERENCE,
            content="Prefers concise, bullet-point explanations.", source="demo",
            created_at=NOW, updated_at=NOW, importance=0.6, user_confirmed=True,
        ),
    ]
    pipeline = PersonalRagPipeline(llm, secure_retriever, memory_retriever)
    result = pipeline.answer(
        QUESTION, requester_id=REQUESTER_ID, requester_tenant_id=TENANT_ID,
        memory_candidates=memory_candidates, top_k_documents=5, top_k_memory=3,
    )

    evidence = {
        r.chunk.id: r.chunk.text
        for r in secure_retriever.search(QUESTION, requester_id=REQUESTER_ID, requester_tenant_id=TENANT_ID, top_k=5)
    }
    grounding = evaluate_grounding(llm, result.answer, evidence)
    citation_score = citation_quality(grounding, set(evidence.keys()))
    latency_ms = (time.monotonic() - start) * 1000

    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": llm.model_name,
        "recall": retrieval_metrics.recall,
        "precision": retrieval_metrics.precision,
        "groundedness_score": grounding.groundedness_score,
        "citation_quality_score": citation_score,
        "latency_ms": latency_ms,
    }
    print(
        f"recall={row['recall']:.2f} precision={row['precision']:.2f} "
        f"groundedness={row['groundedness_score']:.2f} citation_quality={row['citation_quality_score']:.2f} "
        f"latency_ms={row['latency_ms']:.0f}"
    )
    return row


def main() -> None:
    history = _load_history()
    history.append(run_once())
    HISTORY_PATH.write_text(json.dumps(history, indent=2))
    print(f"Appended run #{len(history)} to {HISTORY_PATH}")
    if len(history) < 3:
        print(
            f"Only {len(history)} point(s) of real history so far -- not enough to call "
            "anything a trend yet. Run this script again over time (e.g. before/after a "
            "model or prompt change) to build a real drift signal."
        )


if __name__ == "__main__":
    main()
