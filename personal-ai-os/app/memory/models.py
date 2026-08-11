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
