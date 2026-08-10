def build_positioned_context(filler_chunks: list[str], critical_fact: str, position: str) -> str:
    """Insert critical_fact at 'start', 'middle', or 'end' of the filler chunks,
    for measuring whether answer quality degrades based on fact position (Section 28)."""
    if position not in ("start", "middle", "end"):
        raise ValueError("position must be 'start', 'middle', or 'end'.")

    chunks = list(filler_chunks)
    if position == "start":
        chunks.insert(0, critical_fact)
    elif position == "end":
        chunks.append(critical_fact)
    else:
        chunks.insert(len(chunks) // 2, critical_fact)

    return "\n\n".join(chunks)
