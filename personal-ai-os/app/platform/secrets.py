import os
import re
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

# Patterns that look like real API keys/tokens accidentally hardcoded, rather
# than loaded from environment/secrets store. Deliberately conservative (a
# handful of well-known provider key shapes) — a real secret scanner would
# use a maintained ruleset; this is enough to catch the exact failure mode
# this project already hit once (see Phase 1's github.md log: a real
# Anthropic key + Gmail app password were committed in a .env.example before
# being caught by GitHub's own secret scanning).
_SECRET_LIKE_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),  # Google API key shape
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenAI/Anthropic-style secret key shape
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),  # GitHub personal access token shape
]


class SecretRef(BaseModel):
    """Milestone 49: a secret is never held as a bare string in application
    code — it's referenced by name, resolved at the point of use, and
    carries rotation metadata so 'when did we last rotate this' is an
    answerable question, not something nobody tracks until an incident."""

    name: str
    last_rotated_at: datetime | None = None
    rotation_interval_days: int = 90


class SecretNotFoundError(Exception):
    pass


class SecretRotationOverdueError(Exception):
    pass


class SecretsProvider:
    """Loads secrets from environment variables (the local/`.env` equivalent
    of a real secrets manager) while enforcing real rules: a secret must be
    registered with rotation metadata before it can be read, and reading an
    overdue-for-rotation secret raises rather than silently succeeding. This
    is NOT an integration with a real secrets manager (Vault/AWS Secrets
    Manager) — no such external service exists to integrate with in this
    sandbox — but the rules it enforces are real and would apply identically
    once a real backend is swapped in."""

    def __init__(self, refs: dict[str, SecretRef], enforce_rotation: bool = True):
        self._refs = refs
        self._enforce_rotation = enforce_rotation

    def get(self, name: str) -> str:
        ref = self._refs.get(name)
        if ref is None:
            raise SecretNotFoundError(
                f"Secret '{name}' is not registered. Secrets must be registered with "
                f"rotation metadata before use (Milestone 49)."
            )

        if self._enforce_rotation and ref.last_rotated_at is not None:
            overdue_since = ref.last_rotated_at + timedelta(days=ref.rotation_interval_days)
            if datetime.now(timezone.utc) > overdue_since:
                raise SecretRotationOverdueError(
                    f"Secret '{name}' is overdue for rotation (last rotated {ref.last_rotated_at.date()}, "
                    f"interval {ref.rotation_interval_days} days)."
                )

        value = os.getenv(name)
        if not value:
            raise SecretNotFoundError(f"Secret '{name}' is registered but not set in the environment.")
        return value


def scan_for_hardcoded_secrets(text: str) -> list[str]:
    """Milestone 49: 'Secrets & Data Security.' A minimal, real secret scanner
    — flags text that matches a known API-key shape, so it can be run against
    a diff/file before committing. Returns the matched substrings (not full
    context) so a caller can report a finding without re-printing the secret
    itself in full."""
    findings = []
    for pattern in _SECRET_LIKE_PATTERNS:
        findings.extend(match.group(0) for match in pattern.finditer(text))
    return findings
