from pydantic import BaseModel

from app.retrieval.vector_search import ScoredChunk


class RetrievalCase(BaseModel):
    """A labeled query with the chunk ids that should be considered relevant."""

    query: str
    relevant_chunk_ids: list[str]


class RetrievalMetrics(BaseModel):
    recall: float
    precision: float
    retrieved_ids: list[str]
    relevant_ids: list[str]


def evaluate_retrieval(case: RetrievalCase, results: list[ScoredChunk]) -> RetrievalMetrics:
    retrieved_ids = [r.chunk.id for r in results]
    relevant_set = set(case.relevant_chunk_ids)
    retrieved_set = set(retrieved_ids)

    true_positives = relevant_set & retrieved_set

    recall = len(true_positives) / len(relevant_set) if relevant_set else 1.0
    precision = len(true_positives) / len(retrieved_set) if retrieved_set else 0.0

    return RetrievalMetrics(
        recall=recall,
        precision=precision,
        retrieved_ids=retrieved_ids,
        relevant_ids=case.relevant_chunk_ids,
    )


def average_metrics(all_metrics: list[RetrievalMetrics]) -> dict:
    if not all_metrics:
        return {"recall": 0.0, "precision": 0.0, "n": 0}
    return {
        "recall": sum(m.recall for m in all_metrics) / len(all_metrics),
        "precision": sum(m.precision for m in all_metrics) / len(all_metrics),
        "n": len(all_metrics),
    }
