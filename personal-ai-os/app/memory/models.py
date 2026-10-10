from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    PROFILE = "profile"
    PREFERENCE = "preference"
    GOAL = "goal"
    DECISION = "decision"
    EXPERIENCE = "experience"
    ACHIEVEMENT = "achievement"
    PROJECT = "project"
    RELATIONSHIP = "relationship"
    LEARNING = "learning"
    # Found missing while breaking context/memory down into declarative
    # ("knowing what") vs. procedural ("knowing how") memory at the
    # user's request: every type above is declarative -- a fact ABOUT the
    # user or their situation. PROCEDURE is the first genuinely
    # procedural type: content is a condition -> action rule (e.g. "when
    # asked for code -> keep responses concise"), not a fact to recall,
    # but a behavior to apply. Deliberately added as one more MemoryType
    # value rather than a separate model/store -- it reuses the entire
    # existing write-policy/retrieval/decay pipeline unchanged.
    PROCEDURE = "procedure"


class MemoryStatus(str, Enum):
    """Found missing while adding real conflict handling: every existing
    write was either a fresh insert or a silent duplicate-drop -- there
    was no way to mark an old memory as having been genuinely
    SUPERSEDED by contradicting new information while still keeping it
    around for history (never delete on conflict, matching this
    project's broader never-destroy-on-write discipline, e.g. memory
    decay flags for review rather than deleting)."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"


class MemoryRecord(BaseModel):
    memory_id: str
    tenant_id: str
    user_id: str
    type: MemoryType
    content: str
    source: str
    confidence: float = 1.0
    created_at: datetime
    updated_at: datetime
    importance: float = 0.5
    user_confirmed: bool = False
    status: MemoryStatus = MemoryStatus.ACTIVE
    superseded_by: str | None = None  # memory_id of the record that superseded this one, if any
