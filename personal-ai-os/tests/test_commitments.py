from datetime import date

import pytest

from app.db.connection import get_connection
from app.proactive.commitments import (
    Commitment,
    CommitmentNotFoundError,
    CommitmentOwner,
    CommitmentStatus,
    CommitmentStore,
    detect_commitments,
)
from app.providers.base import LLMProvider


class ScriptedProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    def generate(self, prompt: str) -> str:
        return self._responses.pop(0)

    @property
    def model_name(self) -> str:
        return "scripted-model"


def _store() -> CommitmentStore:
    return CommitmentStore(get_connection(":memory:"))


def test_detect_commitments_extracts_user_commitment():
    llm = ScriptedProvider(['{"commitments": [{"description": "Send the report by Friday", "owner": "user", "due_date": "2026-01-10"}]}'])

    commitments = detect_commitments(llm, "alice", "I'll send the report by Friday.")

    assert len(commitments) == 1
    assert commitments[0].owner == CommitmentOwner.USER
    assert commitments[0].due_date == date(2026, 1, 10)


def test_detect_commitments_extracts_other_party_commitment():
    llm = ScriptedProvider(['{"commitments": [{"description": "Reply with pricing", "owner": "other_party", "due_date": null}]}'])

    commitments = detect_commitments(llm, "alice", "They said they'd get back to me with pricing.")

    assert commitments[0].owner == CommitmentOwner.OTHER_PARTY
    assert commitments[0].due_date is None


def test_detect_commitments_returns_empty_list_when_none_found():
    llm = ScriptedProvider(['{"commitments": []}'])

    commitments = detect_commitments(llm, "alice", "The weather is nice today.")

    assert commitments == []


def test_detect_commitments_rejects_empty_text():
    llm = ScriptedProvider([])

    with pytest.raises(ValueError):
        detect_commitments(llm, "alice", "")


def test_store_save_and_get():
    store = _store()
    commitment = Commitment(owner_id="alice", description="Send report", owner=CommitmentOwner.USER)
    store.save(commitment)

    result = store.get(commitment.commitment_id)

    assert result.description == "Send report"


def test_store_get_missing_raises():
    store = _store()

    with pytest.raises(CommitmentNotFoundError):
        store.get("does-not-exist")


def test_overdue_flags_past_due_open_commitment():
    store = _store()
    commitment = Commitment(owner_id="alice", description="Send report", owner=CommitmentOwner.USER, due_date=date(2026, 1, 1))
    store.save(commitment)

    overdue = store.overdue("alice", as_of=date(2026, 1, 15))

    assert len(overdue) == 1


def test_overdue_excludes_fulfilled_commitments():
    store = _store()
    commitment = Commitment(owner_id="alice", description="Send report", owner=CommitmentOwner.USER, due_date=date(2026, 1, 1))
    store.save(commitment)
    store.update_status(commitment.commitment_id, CommitmentStatus.FULFILLED)

    overdue = store.overdue("alice", as_of=date(2026, 1, 15))

    assert overdue == []


def test_overdue_excludes_commitments_without_due_date():
    store = _store()
    commitment = Commitment(owner_id="alice", description="Someday task", owner=CommitmentOwner.USER, due_date=None)
    store.save(commitment)

    overdue = store.overdue("alice", as_of=date(2026, 1, 15))

    assert overdue == []


def test_commitment_survives_across_store_instances():
    conn = get_connection(":memory:")
    store1 = CommitmentStore(conn)
    commitment = Commitment(owner_id="alice", description="Send report", owner=CommitmentOwner.USER)
    store1.save(commitment)

    store2 = CommitmentStore(conn)
    result = store2.get(commitment.commitment_id)

    assert result.commitment_id == commitment.commitment_id
