from dataclasses import dataclass, field


def estimate_tokens(text: str) -> int:
    """Word count as a token proxy — consistent with the chunking module's convention,
    avoids pulling in a real tokenizer dependency for local experimentation."""
    return len(text.split())


@dataclass
class ContextSection:
    name: str
    content: str
    priority: int  # lower = more important, kept first when compressing


@dataclass
class ContextBuilder:
    """Assembles the final prompt from named sections in a given order, compressing
    (dropping lowest-priority sections first) when a token budget is exceeded.
    Never blindly appends everything (Section 26)."""

    order: list[str] = field(
        default_factory=lambda: ["system", "memory", "retrieved_context", "tool_results", "history", "user"]
    )
    max_tokens: int | None = None

    def build(self, sections: list[ContextSection]) -> str:
        by_name = {s.name: s for s in sections}
        ordered = [by_name[name] for name in self.order if name in by_name]

        if self.max_tokens is None:
            return self._render(ordered)

        kept = self._compress_to_budget(ordered)
        return self._render(kept)

    def _compress_to_budget(self, sections: list[ContextSection]) -> list[ContextSection]:
        # Drop lowest-priority (highest priority number) sections first until under budget.
        remaining = list(sections)
        while remaining and self._total_tokens(remaining) > self.max_tokens:
            remaining.sort(key=lambda s: s.priority)
            remaining.pop()  # drop the current lowest-priority section
        # restore original relative order after compression
        kept_names = {s.name for s in remaining}
        return [s for s in sections if s.name in kept_names]

    def _total_tokens(self, sections: list[ContextSection]) -> int:
        return sum(estimate_tokens(s.content) for s in sections)

    def _render(self, sections: list[ContextSection]) -> str:
        return "\n\n".join(f"### {s.name}\n{s.content}" for s in sections if s.content)
