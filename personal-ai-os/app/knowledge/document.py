from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Sensitivity(str, Enum):
    PUBLIC = "PUBLIC"
    PERSONAL = "PERSONAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    HIGHLY_SENSITIVE = "HIGHLY_SENSITIVE"


class PersonalDocumentMetadata(BaseModel):
    """Matches Section 9's metadata schema plus Section 10's security fields.
    Every ingested personal document must carry all of this — there is no
    'metadata-optional' path."""

    document_id: str
    source: str
    title: str
    created_at: datetime
    updated_at: datetime
    version: int = 1
    category: str = "uncategorized"
    sensitivity: Sensitivity = Sensitivity.PERSONAL
    owner_id: str
    tenant_id: str
    permissions: list[str] = Field(default_factory=list)


class PersonalDocument(BaseModel):
    metadata: PersonalDocumentMetadata
    text: str
