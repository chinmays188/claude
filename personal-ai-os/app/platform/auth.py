import base64
import hashlib
import hmac
import json
import time
from enum import Enum

from pydantic import BaseModel


class Role(str, Enum):
    """Milestone 48/50: roles map to permission sets. Kept small and
    explicit — a real system would let admins define custom roles, but a
    fixed set is enough to demonstrate real RBAC without inventing a role
    management UI this project has no use for yet."""

    VIEWER = "viewer"  # read-only
    OPERATOR = "operator"  # can act, still subject to approval gates
    ADMIN = "admin"  # full permissions, including admin-only tools


_ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.VIEWER: {"read:github", "read:calendar", "read:email", "read:retrieval", "compute:local"},
    Role.OPERATOR: {
        "read:github", "read:calendar", "read:email", "read:retrieval", "compute:local",
        "write:email", "write:calendar",
    },
    Role.ADMIN: {
        "read:github", "read:calendar", "read:email", "read:retrieval", "compute:local",
        "write:email", "write:calendar", "admin:tenant",
    },
}


def permissions_for_role(role: Role) -> set[str]:
    return set(_ROLE_PERMISSIONS[role])


class TokenPayload(BaseModel):
    user_id: str
    tenant_id: str
    role: Role
    issued_at: float
    expires_at: float


class InvalidTokenError(Exception):
    pass


class TokenExpiredError(InvalidTokenError):
    pass


class TokenIssuer:
    """Milestone 48: a real, HMAC-signed, JWT-shaped token
    (base64(header).base64(payload).base64(hmac-signature)) — issued and
    verified with stdlib crypto, no external identity provider needed to
    exercise real auth logic locally. `secret_key` plays the role a real
    deployment's signing secret would (see Milestone 49 for how that secret
    itself should be handled)."""

    def __init__(self, secret_key: str, ttl_seconds: float = 3600.0):
        if not secret_key:
            raise ValueError("secret_key must not be empty.")
        self._secret_key = secret_key.encode()
        self._ttl_seconds = ttl_seconds

    def issue(self, user_id: str, tenant_id: str, role: Role) -> str:
        now = time.time()
        payload = TokenPayload(user_id=user_id, tenant_id=tenant_id, role=role, issued_at=now, expires_at=now + self._ttl_seconds)

        header_b64 = _b64_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        payload_b64 = _b64_encode(payload.model_dump_json().encode())
        signing_input = f"{header_b64}.{payload_b64}".encode()
        signature = hmac.new(self._secret_key, signing_input, hashlib.sha256).digest()
        signature_b64 = _b64_encode(signature)

        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def verify(self, token: str) -> TokenPayload:
        parts = token.split(".")
        if len(parts) != 3:
            raise InvalidTokenError("Token does not have the expected header.payload.signature shape.")
        header_b64, payload_b64, signature_b64 = parts

        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_signature = hmac.new(self._secret_key, signing_input, hashlib.sha256).digest()
        actual_signature = _b64_decode(signature_b64)

        if not hmac.compare_digest(expected_signature, actual_signature):
            raise InvalidTokenError("Token signature is invalid.")

        try:
            payload = TokenPayload.model_validate_json(_b64_decode(payload_b64))
        except Exception as exc:
            raise InvalidTokenError(f"Token payload could not be parsed: {exc}") from exc

        if time.time() > payload.expires_at:
            raise TokenExpiredError(f"Token expired at {payload.expires_at}.")

        return payload


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)
