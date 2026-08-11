from pydantic import BaseModel


class InteractionResult(BaseModel):
    mode: str  # "voice" | "text"
    task_completed: bool
    latency_ms: float
    correction_needed: bool = False  # user had to repeat/rephrase


class InteractionComparison(BaseModel):
    voice_task_completion_rate: float
    text_task_completion_rate: float
    voice_avg_latency_ms: float
    text_avg_latency_ms: float
    voice_correction_rate: float
    text_correction_rate: float


def compare_interactions(results: list[InteractionResult]) -> InteractionComparison:
    """Section 8 (M18 evaluation): compare voice vs. text interaction quality —
    never assume voice is 'the same but spoken', measure it independently."""
    voice = [r for r in results if r.mode == "voice"]
    text = [r for r in results if r.mode == "text"]

    return InteractionComparison(
        voice_task_completion_rate=_rate(voice, lambda r: r.task_completed),
        text_task_completion_rate=_rate(text, lambda r: r.task_completed),
        voice_avg_latency_ms=_avg(voice, lambda r: r.latency_ms),
        text_avg_latency_ms=_avg(text, lambda r: r.latency_ms),
        voice_correction_rate=_rate(voice, lambda r: r.correction_needed),
        text_correction_rate=_rate(text, lambda r: r.correction_needed),
    )


def _rate(results: list[InteractionResult], predicate) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if predicate(r)) / len(results)


def _avg(results: list[InteractionResult], value_fn) -> float:
    if not results:
        return 0.0
    return sum(value_fn(r) for r in results) / len(results)
