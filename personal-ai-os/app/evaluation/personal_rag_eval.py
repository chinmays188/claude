from datetime import datetime

from pydantic import BaseModel

from app.memory.retrieval import RankedMemory


class MemoryRetrievalCase(BaseModel):
    """A labeled query with the memory ids that should have been retrieved,
    mirroring RetrievalCase (app/evaluation/retrieval_eval.py) but for memory
    instead of document chunks."""

    query: str
    relevant_memory_ids: list[str]


class MemoryRetrievalMetrics(BaseModel):
    memory_precision: float
    memory_recall: float
    retrieved_ids: list[str]
    relevant_ids: list[str]


def evaluate_memory_retrieval(
    case: MemoryRetrievalCase, results: list[RankedMemory]
) -> MemoryRetrievalMetrics:
    """Section 16: 'Memory precision — did the system retrieve the correct
    personal memory?' and 'Memory recall — did it retrieve all relevant memories?'"""
    retrieved_ids = [r.memory.memory_id for r in results]
    relevant_set = set(case.relevant_memory_ids)
    retrieved_set = set(retrieved_ids)
    true_positives = relevant_set & retrieved_set

    precision = len(true_positives) / len(retrieved_set) if retrieved_set else 0.0
    recall = len(true_positives) / len(relevant_set) if relevant_set else 1.0

    return MemoryRetrievalMetrics(
        memory_precision=precision, memory_recall=recall,
        retrieved_ids=retrieved_ids, relevant_ids=case.relevant_memory_ids,
    )


def personalization_score(answer: str, expected_personal_markers: list[str]) -> float:
    """Section 16: 'Personalization — did the response use relevant personal
    context?' A simple, auditable proxy: what fraction of expected personal
    details (names, project names, specific facts only in this user's memory)
    actually appear in the answer. Not a semantic judge — a literal presence
    check, since personalization here means citing *specific* known facts, not
    a vague tone match."""
    if not expected_personal_markers:
        return 1.0
    answer_lower = answer.lower()
    present = sum(1 for marker in expected_personal_markers if marker.lower() in answer_lower)
    return present / len(expected_personal_markers)


def temporal_correctness(
    retrieved_timestamps: list[datetime], expected_period_start: datetime, expected_period_end: datetime
) -> float:
    """Section 16: 'Temporal correctness — did it retrieve information from the
    correct time period?' Fraction of retrieved items whose timestamp actually
    falls within the expected window (e.g. 'last month')."""
    if not retrieved_timestamps:
        return 0.0
    in_range = sum(1 for ts in retrieved_timestamps if expected_period_start <= ts <= expected_period_end)
    return in_range / len(retrieved_timestamps)
