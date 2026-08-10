import pytest

from app.context.lost_in_middle import build_positioned_context


def test_places_fact_at_start():
    result = build_positioned_context(["chunk1", "chunk2", "chunk3"], "CRITICAL_FACT", "start")

    assert result.startswith("CRITICAL_FACT")


def test_places_fact_at_end():
    result = build_positioned_context(["chunk1", "chunk2", "chunk3"], "CRITICAL_FACT", "end")

    assert result.endswith("CRITICAL_FACT")


def test_places_fact_in_middle():
    filler = [f"chunk{i}" for i in range(10)]
    result = build_positioned_context(filler, "CRITICAL_FACT", "middle")
    chunks = result.split("\n\n")

    middle_index = len(chunks) // 2
    assert chunks[middle_index] == "CRITICAL_FACT"


def test_invalid_position_raises():
    with pytest.raises(ValueError):
        build_positioned_context(["a"], "fact", "somewhere")
