import pytest

from app.platform.auth import Role, TokenPayload
from app.platform.tenancy import CrossTenantAccessError, TenantContext, enforce_same_tenant


def test_from_token_payload_derives_context():
    payload = TokenPayload(user_id="alice", tenant_id="t1", role=Role.OPERATOR, issued_at=0, expires_at=1)

    context = TenantContext.from_token_payload(payload)

    assert context.tenant_id == "t1"
    assert context.user_id == "alice"
    assert context.role == Role.OPERATOR


def test_enforce_same_tenant_passes_for_matching_tenant():
    context = TenantContext(tenant_id="t1", user_id="alice", role=Role.VIEWER)

    enforce_same_tenant(context, resource_tenant_id="t1")  # should not raise


def test_enforce_same_tenant_raises_for_cross_tenant_access():
    context = TenantContext(tenant_id="t1", user_id="alice", role=Role.VIEWER)

    with pytest.raises(CrossTenantAccessError):
        enforce_same_tenant(context, resource_tenant_id="t2")
