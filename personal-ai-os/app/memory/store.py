from pydantic import BaseModel


class MemoryEntry(BaseModel):
    tenant_id: str
    user_id: str
    session_id: str
    key: str
    value: str


class CrossTenantAccessError(Exception):
    pass


class MemoryStore:
    """In-memory key-value store scoped by (tenant_id, user_id, session_id).
    Section 55: isolation is enforced by application code, never left to the LLM
    to respect. Every read/write requires an explicit scope; there is no
    'query everything' method, by design."""

    def __init__(self):
        self._entries: dict[tuple[str, str, str, str], str] = {}

    def write(self, tenant_id: str, user_id: str, session_id: str, key: str, value: str) -> None:
        self._entries[(tenant_id, user_id, session_id, key)] = value

    def read(self, tenant_id: str, user_id: str, session_id: str, key: str) -> str | None:
        return self._entries.get((tenant_id, user_id, session_id, key))

    def list_keys(self, tenant_id: str, user_id: str, session_id: str) -> list[str]:
        return [
            k for (t, u, s, k) in self._entries
            if t == tenant_id and u == user_id and s == session_id
        ]
