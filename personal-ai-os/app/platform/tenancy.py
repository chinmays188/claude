from pydantic import BaseModel

from app.platform.auth import Role, TokenPayload


class TenantContext(BaseModel):
    """Milestone 50: the single object every request-scoped operation should
    be given, so tenant/user isolation is derived from one verified source
    (a validated auth token, Milestone 48) rather than trusted from whatever
    a caller happened to pass in. Every Phase 2/3 store already takes
    explicit tenant_id/owner_id parameters (MemoryStore, GoalStore, TaskStore,
    GraphStore, etc.) — this formalizes where those values should come from
    in a real multi-tenant deployment: the verified token, never a raw
    request parameter a client could spoof."""

    tenant_id: str
    user_id: str
    role: Role

    @classmethod
    def from_token_payload(cls, payload: TokenPayload) -> "TenantContext":
        return cls(tenant_id=payload.tenant_id, user_id=payload.user_id, role=payload.role)


class CrossTenantAccessError(Exception):
    pass


def enforce_same_tenant(context: TenantContext, resource_tenant_id: str) -> None:
    """Milestone 50's core rule, made a single reusable check: a request
    context must never be allowed to touch a resource belonging to a
    different tenant, regardless of what the caller passed as an id
    (Section 55, carried forward from Phase 1's memory/store.py, now made a
    shared platform-level utility rather than duplicated per-store logic)."""
    if context.tenant_id != resource_tenant_id:
        raise CrossTenantAccessError(
            f"Context is scoped to tenant '{context.tenant_id}' but resource "
            f"belongs to tenant '{resource_tenant_id}'."
        )
