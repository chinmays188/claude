from datetime import datetime

from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str
    text: str
    source: str
    created_at: datetime
    updated_at: datetime
    version: int = 1


class Chunk(BaseModel):
    id: str
    document_id: str
    text: str
    source: str
    created_at: datetime
    updated_at: datetime
    chunk_index: int
