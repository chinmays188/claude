from app.context.builder import ContextBuilder, ContextSection, estimate_tokens


def test_estimate_tokens_counts_words():
    assert estimate_tokens("one two three") == 3
    assert estimate_tokens("") == 0


def test_orders_sections_per_configured_order():
    builder = ContextBuilder(order=["system", "user"])
    sections = [
        ContextSection(name="user", content="Explain RAG.", priority=1),
        ContextSection(name="system", content="You are a research agent.", priority=0),
    ]

    result = builder.build(sections)

    assert result.index("system") < result.index("user")


def test_sections_not_in_order_list_are_dropped():
    builder = ContextBuilder(order=["system"])
    sections = [
        ContextSection(name="system", content="sys", priority=0),
        ContextSection(name="mystery", content="should not appear", priority=5),
    ]

    result = builder.build(sections)

    assert "mystery" not in result
    assert "should not appear" not in result


def test_empty_content_sections_are_omitted():
    builder = ContextBuilder(order=["system", "memory"])
    sections = [
        ContextSection(name="system", content="sys", priority=0),
        ContextSection(name="memory", content="", priority=1),
    ]

    result = builder.build(sections)

    assert "memory" not in result


def test_no_budget_keeps_everything():
    builder = ContextBuilder(order=["system", "history"], max_tokens=None)
    sections = [
        ContextSection(name="system", content="a b c", priority=0),
        ContextSection(name="history", content="d e f g h i j k", priority=5),
    ]

    result = builder.build(sections)

    assert "d e f g h i j k" in result


def test_compression_drops_lowest_priority_section_first():
    builder = ContextBuilder(order=["system", "history"], max_tokens=5)
    sections = [
        ContextSection(name="system", content="a b c", priority=0),
        ContextSection(name="history", content="d e f g h i j k", priority=5),
    ]

    result = builder.build(sections)

    assert "system" in result
    assert "history" not in result


def test_compression_keeps_original_relative_order_of_survivors():
    builder = ContextBuilder(order=["system", "memory", "history"], max_tokens=10)
    sections = [
        ContextSection(name="system", content="a b", priority=0),
        ContextSection(name="memory", content="c d", priority=1),
        ContextSection(name="history", content="e f g h i j k l m n", priority=9),
    ]

    result = builder.build(sections)

    assert result.index("system") < result.index("memory")
    assert "history" not in result


def test_compression_can_drop_everything_if_budget_too_small():
    builder = ContextBuilder(order=["system"], max_tokens=0)
    sections = [ContextSection(name="system", content="a b c", priority=0)]

    result = builder.build(sections)

    assert result == ""
