from app.agents.multi_agent_coordinator import might_need_multiple_agents


def test_short_simple_request_does_not_trigger():
    assert might_need_multiple_agents("Explain RAG.") is False


def test_short_simple_comparison_does_not_trigger():
    assert might_need_multiple_agents("Compare RAG and fine-tuning.") is False


def test_sequencing_keyword_triggers_even_if_short():
    assert might_need_multiple_agents("Research X, then compare it to Y.") is True


def test_long_request_triggers_by_word_count():
    long_text = (
        "I want you to look into the current state of container orchestration "
        "platforms, weigh their tradeoffs for a mid-size team, and figure out "
        "what our rollout should look like over the next quarter."
    )
    assert might_need_multiple_agents(long_text) is True


def test_and_also_triggers():
    assert might_need_multiple_agents("Explain RAG and also compare it to fine-tuning.") is True
