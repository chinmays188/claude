from app.proactive.events import Event, EventBus, EventType


def test_publish_delivers_to_subscriber():
    bus = EventBus()
    received = []
    bus.subscribe(EventType.TASK_STATE_CHANGED, lambda e: received.append(e))

    event = Event(type=EventType.TASK_STATE_CHANGED, owner_id="alice", payload={})
    bus.publish(event)

    assert len(received) == 1
    assert received[0].event_id == event.event_id


def test_publish_does_not_deliver_to_wrong_type_subscriber():
    bus = EventBus()
    received = []
    bus.subscribe(EventType.EMAIL_RECEIVED, lambda e: received.append(e))

    bus.publish(Event(type=EventType.TASK_STATE_CHANGED, owner_id="alice", payload={}))

    assert received == []


def test_multiple_subscribers_all_receive_event():
    bus = EventBus()
    received_a, received_b = [], []
    bus.subscribe(EventType.GOAL_UPDATED, lambda e: received_a.append(e))
    bus.subscribe(EventType.GOAL_UPDATED, lambda e: received_b.append(e))

    bus.publish(Event(type=EventType.GOAL_UPDATED, owner_id="alice", payload={}))

    assert len(received_a) == 1
    assert len(received_b) == 1


def test_history_returns_all_published_events():
    bus = EventBus()
    bus.publish(Event(type=EventType.GOAL_UPDATED, owner_id="alice", payload={}))
    bus.publish(Event(type=EventType.TASK_STATE_CHANGED, owner_id="bob", payload={}))

    assert len(bus.history()) == 2


def test_history_scoped_to_owner():
    bus = EventBus()
    bus.publish(Event(type=EventType.GOAL_UPDATED, owner_id="alice", payload={}))
    bus.publish(Event(type=EventType.GOAL_UPDATED, owner_id="bob", payload={}))

    alice_history = bus.history(owner_id="alice")

    assert len(alice_history) == 1
    assert alice_history[0].owner_id == "alice"
