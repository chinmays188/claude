import time

import pytest

from app.platform.auth import (
    InvalidTokenError,
    Role,
    TokenExpiredError,
    TokenIssuer,
    permissions_for_role,
)


def test_issue_and_verify_round_trip():
    issuer = TokenIssuer(secret_key="test-secret")
    token = issuer.issue(user_id="alice", tenant_id="t1", role=Role.OPERATOR)

    payload = issuer.verify(token)

    assert payload.user_id == "alice"
    assert payload.tenant_id == "t1"
    assert payload.role == Role.OPERATOR


def test_tampered_payload_fails_verification():
    issuer = TokenIssuer(secret_key="test-secret")
    token = issuer.issue(user_id="alice", tenant_id="t1", role=Role.VIEWER)
    header_b64, payload_b64, sig_b64 = token.split(".")

    # Flip a character in the payload to simulate tampering (e.g. trying to
    # escalate role client-side) without knowing the secret.
    tampered_payload = payload_b64[:-1] + ("A" if payload_b64[-1] != "A" else "B")
    tampered_token = f"{header_b64}.{tampered_payload}.{sig_b64}"

    with pytest.raises(InvalidTokenError):
        issuer.verify(tampered_token)


def test_wrong_secret_key_fails_verification():
    issuer_a = TokenIssuer(secret_key="secret-a")
    issuer_b = TokenIssuer(secret_key="secret-b")
    token = issuer_a.issue(user_id="alice", tenant_id="t1", role=Role.VIEWER)

    with pytest.raises(InvalidTokenError):
        issuer_b.verify(token)


def test_expired_token_raises_token_expired_error():
    issuer = TokenIssuer(secret_key="test-secret", ttl_seconds=0.01)
    token = issuer.issue(user_id="alice", tenant_id="t1", role=Role.VIEWER)

    time.sleep(0.05)

    with pytest.raises(TokenExpiredError):
        issuer.verify(token)


def test_malformed_token_raises_invalid_token_error():
    issuer = TokenIssuer(secret_key="test-secret")

    with pytest.raises(InvalidTokenError):
        issuer.verify("not.a.valid.token.shape")


def test_empty_secret_key_rejected():
    with pytest.raises(ValueError):
        TokenIssuer(secret_key="")


def test_viewer_role_has_no_write_permissions():
    perms = permissions_for_role(Role.VIEWER)

    assert "write:email" not in perms
    assert "read:github" in perms


def test_admin_role_has_admin_permission():
    perms = permissions_for_role(Role.ADMIN)

    assert "admin:tenant" in perms


def test_operator_role_has_write_but_not_admin():
    perms = permissions_for_role(Role.OPERATOR)

    assert "write:email" in perms
    assert "admin:tenant" not in perms
