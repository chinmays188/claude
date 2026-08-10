import time
import uuid
from contextlib import contextmanager

from pydantic import BaseModel, Field


class Span(BaseModel):
    span_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    kind: str  # "input" | "classification" | "agent" | "llm" | "tool" | "retrieval" | "evaluation" | "output"
    started_at: float
    ended_at: float | None = None
    status: str = "success"
    error: str | None = None
    metadata: dict = Field(default_factory=dict)
    children: list["Span"] = Field(default_factory=list)

    @property
    def duration_ms(self) -> float | None:
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at) * 1000


class Trace(BaseModel):
    execution_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str
    user_id: str
    agent: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    retrieval_calls: int = 0
    latency_ms: float = 0.0
    cost: float = 0.0
    status: str = "success"
    spans: list[Span] = Field(default_factory=list)


class TraceRecorder:
    """Records a trace and its nested spans for one execution. Not a full
    OpenTelemetry integration — a lightweight, self-contained recorder matching
    the trace schema in Section 47, sufficient for local/SQLite-backed observability."""

    def __init__(self, session_id: str, user_id: str):
        self.trace = Trace(session_id=session_id, user_id=user_id)
        self._start_time = time.monotonic()
        self._span_stack: list[Span] = []

    @contextmanager
    def span(self, name: str, kind: str, **metadata):
        span = Span(name=name, kind=kind, started_at=time.monotonic(), metadata=metadata)
        parent = self._span_stack[-1] if self._span_stack else None
        self._span_stack.append(span)
        try:
            yield span
        except Exception as exc:
            span.status = "error"
            span.error = str(exc)
            raise
        finally:
            span.ended_at = time.monotonic()
            self._span_stack.pop()
            if parent is not None:
                parent.children.append(span)
            else:
                self.trace.spans.append(span)

            if kind == "tool":
                self.trace.tool_calls += 1
            elif kind == "retrieval":
                self.trace.retrieval_calls += 1

    def finish(self, status: str = "success") -> Trace:
        self.trace.status = status
        self.trace.latency_ms = (time.monotonic() - self._start_time) * 1000
        return self.trace
