"""Generates real, end-to-end RAG pipeline examples for the dashboard's RAG
page, by actually running the real pipeline (chunking, real embeddings,
real FAISS + BM25 hybrid search, real cross-encoder reranking, real
context building, a real Gemini generation call, and real grounding/
citation evaluation) -- never hand-written.

Kept separate from the page's live/interactive chunking+search demo (which
runs for free, no LLM call, directly on whatever the user pastes) because
generation and grounding-eval cost real API calls -- this script is run
once locally to produce a fixed, committed set of examples, same pattern
as scripts/generate_tool_examples.py.

Usage:
    PYTHONPATH=. python scripts/generate_rag_examples.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import require_gemini_key
from app.context.builder import ContextBuilder, ContextSection
from app.evaluation.grounding_eval import citation_quality, evaluate_grounding
from app.evaluation.retrieval_eval import RetrievalCase, evaluate_retrieval
from app.knowledge.document import PersonalDocumentMetadata, Sensitivity
from app.knowledge.secure_retrieval import SecureRetriever
from app.memory.models import MemoryRecord, MemoryType
from app.memory.retrieval import MemoryRetriever
from app.personal_rag.pipeline import PersonalRagPipeline
from app.providers.gemini_provider import GeminiProvider
from app.retrieval.chunking import chunk_document
from app.retrieval.document import Chunk, Document
from app.retrieval.embeddings import SentenceTransformerEmbedding
from app.retrieval.hybrid_search import HybridSearch, reciprocal_rank_fusion
from app.retrieval.keyword_search import KeywordSearch
from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.vector_search import VectorStore

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "app" / "dashboard_ui" / "rag_examples.json"
NOW = datetime.now(timezone.utc)
REQUESTER_ID = "demo_user"
TENANT_ID = "demo_tenant"

# Real, fabricated-but-labeled-as-such synthetic achievements -- same
# convention this project uses everywhere (no real personal data), reused
# from tests/fakes/example_resume.py so this isn't yet another ad hoc
# fixture.
DOCUMENTS = [
    ("achv1", "Led a cross-functional team of 6 to launch a self-serve refund flow, "
              "reducing average refund resolution time from 5 days to 8 hours."),
    ("achv2", "Resolved a conflict between engineering and support teams over incident "
              "ownership by proposing a shared on-call rotation, which both teams "
              "adopted within a month."),
    ("achv3", "Designed and shipped an AI-assisted email triage system that reduced "
              "first-response time for post-sales tickets by 40%."),
    ("achv4", "Kubernetes is a container orchestration platform that automates "
              "deployment, scaling, and operations of application containers across "
              "clusters of hosts."),
]

QUESTION = "What did I do to improve customer support response times, and do I have any Kubernetes experience?"

# Real, honestly-labeled ground truth for retrieval-eval (recall/precision
# need a human-labeled "what SHOULD have been retrieved" -- constructed
# here deliberately, not inferred from a live run, per
# app/evaluation/retrieval_eval.py's actual requirement).
RETRIEVAL_GROUND_TRUTH = RetrievalCase(
    query=QUESTION,
    relevant_chunk_ids=["achv1::chunk0", "achv3::chunk0", "achv4::chunk0"],
)


def build_stores():
    embedding_model = SentenceTransformerEmbedding()
    vector_store = VectorStore(embedding_model)
    keyword_store = KeywordSearch()
    metadata = {}
    all_chunks: list[Chunk] = []

    for doc_id, text in DOCUMENTS:
        doc = Document(id=doc_id, text=text, source="resume", created_at=NOW, updated_at=NOW)
        chunks = chunk_document(doc, chunk_size=150, overlap=30)
        vector_store.add(chunks)
        keyword_store.add(chunks)
        all_chunks.extend(chunks)
        metadata[doc_id] = PersonalDocumentMetadata(
            document_id=doc_id, source="resume", title="Achievements", created_at=NOW, updated_at=NOW,
            category="career", sensitivity=Sensitivity.PERSONAL, owner_id=REQUESTER_ID, tenant_id=TENANT_ID,
        )

    return vector_store, keyword_store, all_chunks, metadata


def main() -> None:
    require_gemini_key()
    llm = GeminiProvider()  # this project's configured default (gemini-3.5-flash-lite)

    vector_store, keyword_store, all_chunks, metadata = build_stores()
    secure_retriever = SecureRetriever(vector_store, metadata)

    # --- Stage-by-stage real trace, captured for the page ---
    vector_results = vector_store.search(QUESTION, top_k=10)
    keyword_results = keyword_store.search(QUESTION, top_k=10)
    fused = reciprocal_rank_fusion([vector_results, keyword_results])

    reranker = CrossEncoderReranker()
    reranked = reranker.rerank(QUESTION, fused, top_k=5)

    retrieval_metrics = evaluate_retrieval(RETRIEVAL_GROUND_TRUTH, reranked)

    # --- Full pipeline (memory + document retrieval -> context -> generate) ---
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

    evidence = {r.chunk.id: r.chunk.text for r in secure_retriever.search(QUESTION, requester_id=REQUESTER_ID, requester_tenant_id=TENANT_ID, top_k=5)}
    grounding = evaluate_grounding(llm, result.answer, evidence)
    valid_ids = set(evidence.keys())
    citation_score = citation_quality(grounding, valid_ids)

    example = {
        "documents": [{"id": doc_id, "text": text} for doc_id, text in DOCUMENTS],
        "chunks": [
            {"id": c.id, "document_id": c.document_id, "text": c.text, "word_count": len(c.text.split())}
            for c in all_chunks
        ],
        "question": QUESTION,
        "vector_search_results": [
            {"chunk_id": r.chunk.id, "score": r.score, "text": r.chunk.text} for r in vector_results
        ],
        "keyword_search_results": [
            {"chunk_id": r.chunk.id, "score": r.score, "text": r.chunk.text} for r in keyword_results
        ],
        "fused_results": [{"chunk_id": r.chunk.id, "score": r.score} for r in fused],
        "reranked_results": [
            {"chunk_id": r.chunk.id, "score": r.score, "text": r.chunk.text} for r in reranked
        ],
        "retrieval_ground_truth": RETRIEVAL_GROUND_TRUTH.relevant_chunk_ids,
        "retrieval_metrics": {
            "recall": retrieval_metrics.recall, "precision": retrieval_metrics.precision,
            "retrieved_ids": retrieval_metrics.retrieved_ids, "relevant_ids": retrieval_metrics.relevant_ids,
        },
        "final_answer": result.answer,
        "citations": [{"chunk_id": c.chunk_id, "source": c.source} for c in result.citations],
        "memory_used": result.memory_used,
        "grounding": {
            "grounded_claim_count": grounding.grounded_claim_count,
            "unsupported_claim_count": grounding.unsupported_claim_count,
            "groundedness_score": grounding.groundedness_score,
            "citations": [{"claim": c.claim, "chunk_id": c.chunk_id} for c in grounding.citations],
        },
        "citation_quality_score": citation_score,
    }

    OUTPUT_PATH.write_text(json.dumps(example, indent=2, default=str))
    print(f"Wrote real RAG pipeline example to {OUTPUT_PATH}")
    print(f"Recall: {retrieval_metrics.recall:.2f}, Precision: {retrieval_metrics.precision:.2f}")
    print(f"Groundedness: {grounding.groundedness_score:.2f}, Citation quality: {citation_score:.2f}")


if __name__ == "__main__":
    main()
