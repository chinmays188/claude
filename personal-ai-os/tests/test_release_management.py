import pytest

from app.db.connection import get_connection
from app.platform.release_management import ReleaseManager, ReleaseNotFoundError


def _manager() -> ReleaseManager:
    return ReleaseManager(get_connection(":memory:"))


def test_publish_creates_version_1_and_activates_it():
    manager = _manager()

    record = manager.publish("research_agent_prompt", "You are a research agent.")

    assert record.version == 1
    assert record.is_active


def test_publish_increments_version_and_deactivates_previous():
    manager = _manager()
    manager.publish("research_agent_prompt", "v1 content")
    v2 = manager.publish("research_agent_prompt", "v2 content")

    active = manager.active("research_agent_prompt")

    assert active.version == 2
    assert active.content == "v2 content"

    history = manager.history("research_agent_prompt")
    v1_record = next(r for r in history if r.version == 1)
    assert not v1_record.is_active


def test_active_raises_when_nothing_published():
    manager = _manager()

    with pytest.raises(ReleaseNotFoundError):
        manager.active("never_published")


def test_rollback_reactivates_previous_version():
    manager = _manager()
    manager.publish("research_agent_prompt", "v1 content")
    manager.publish("research_agent_prompt", "v2 content")

    rolled_back = manager.rollback("research_agent_prompt")

    assert rolled_back.version == 1
    assert rolled_back.content == "v1 content"
    assert manager.active("research_agent_prompt").version == 1


def test_rollback_raises_with_only_one_version():
    manager = _manager()
    manager.publish("research_agent_prompt", "v1 content")

    with pytest.raises(ReleaseNotFoundError):
        manager.rollback("research_agent_prompt")


def test_history_survives_across_manager_instances():
    conn = get_connection(":memory:")
    manager1 = ReleaseManager(conn)
    manager1.publish("component_x", "v1")

    manager2 = ReleaseManager(conn)
    active = manager2.active("component_x")

    assert active.content == "v1"
