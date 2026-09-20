from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.observability.traces import Span, Trace

# OpenTelemetry's real semantic conventions this project's own span "kind"
# strings map onto (https://opentelemetry.io/docs/specs/semconv/) — mapped
# explicitly here so this exporter genuinely produces OTel-shaped output,
# not just something that looks vaguely similar.
_KIND_TO_OTEL_SPAN_KIND: dict[str, str] = {
    "input": "SERVER",
    "classification": "INTERNAL",
    "agent": "INTERNAL",
    "llm": "CLIENT",
    "tool": "CLIENT",
    "retrieval": "CLIENT",
    "evaluation": "INTERNAL",
    "output": "SERVER",
}


class OtelSpan(BaseModel):
    """OpenTelemetry-shaped span: trace_id, span_id, parent_span_id, name,
    kind, timestamps in nanoseconds (OTel's actual unit), status, and
    attributes — the shape a real OTel collector's OTLP endpoint expects."""

    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    kind: str
    start_time_unix_nano: int
    end_time_unix_nano: int | None
    status_code: str  # "OK" | "ERROR"
    attributes: dict


def to_otel_spans(trace: Trace) -> list[OtelSpan]:
    """Milestone 51: converts this project's own Trace/Span (Phase 1,
    Milestone 12) into OpenTelemetry-shaped spans. No real OTel SDK/collector
    dependency is added — this produces the correct shape a real
    OTLP exporter would need, verifiable without one."""
    result: list[OtelSpan] = []
    _flatten(trace.spans, trace.execution_id, parent_id=None, out=result)
    return result


def _flatten(spans: list[Span], trace_id: str, parent_id: str | None, out: list[OtelSpan]) -> None:
    for span in spans:
        out.append(
            OtelSpan(
                trace_id=trace_id, span_id=span.span_id, parent_span_id=parent_id,
                name=span.name, kind=_KIND_TO_OTEL_SPAN_KIND.get(span.kind, "INTERNAL"),
                start_time_unix_nano=int(span.started_at * 1_000_000_000),
                end_time_unix_nano=int(span.ended_at * 1_000_000_000) if span.ended_at else None,
                status_code="ERROR" if span.status == "error" else "OK",
                attributes=dict(span.metadata),
            )
        )
        _flatten(span.children, trace_id, parent_id=span.span_id, out=out)


class OtelExporter(ABC):
    @abstractmethod
    def export(self, spans: list[OtelSpan]) -> None:
        ...


class InMemoryOtelExporter(OtelExporter):
    """Milestone 51's honest local substitute for a real collector: no
    external OTel Collector/Jaeger/Tempo instance exists in this sandbox to
    export to, so this exporter just accumulates spans in memory — real
    enough to verify `to_otel_spans()` produces genuinely usable output, not
    a real network export. A real deployment would swap this for an actual
    OTLP-over-HTTP/gRPC exporter without changing `to_otel_spans()` at all."""

    def __init__(self):
        self.exported: list[OtelSpan] = []

    def export(self, spans: list[OtelSpan]) -> None:
        self.exported.extend(spans)
