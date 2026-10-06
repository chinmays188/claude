from pydantic import BaseModel

from app.observability.traces import Span, Trace


class LatencyBreakdown(BaseModel):
    """Real aggregation of a Trace's existing Span.duration_ms data, by
    span kind (classification/agent/llm/tool/retrieval/evaluation/etc.) --
    found missing while investigating 'AI Cost & Latency Engineering':
    duration_ms was already captured per span, but never aggregated
    anywhere; the dashboard only ever showed it per-span in a raw tree.
    Flattens nested spans (a tool call inside an agent span still counts
    toward 'tool', not double-counted into 'agent')."""

    by_kind_ms: dict[str, float]
    total_span_ms: float
    unaccounted_ms: float  # trace.latency_ms minus everything attributed to a span

    def share_by_kind(self) -> dict[str, float]:
        """Each kind's share of total_span_ms, as a 0-1 fraction."""
        if self.total_span_ms == 0:
            return {kind: 0.0 for kind in self.by_kind_ms}
        return {kind: ms / self.total_span_ms for kind, ms in self.by_kind_ms.items()}


def _flatten(spans: list[Span]) -> list[Span]:
    flat: list[Span] = []
    for span in spans:
        flat.append(span)
        flat.extend(_flatten(span.children))
    return flat


def compute_latency_breakdown(trace: Trace) -> LatencyBreakdown:
    by_kind: dict[str, float] = {}
    for span in _flatten(trace.spans):
        if span.duration_ms is None:
            continue
        by_kind[span.kind] = by_kind.get(span.kind, 0.0) + span.duration_ms

    total_span_ms = sum(by_kind.values())
    unaccounted_ms = max(0.0, trace.latency_ms - total_span_ms)
    return LatencyBreakdown(by_kind_ms=by_kind, total_span_ms=total_span_ms, unaccounted_ms=unaccounted_ms)
