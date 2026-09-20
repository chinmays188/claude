import os
from datetime import datetime, timedelta, timezone

import pytest

from app.platform.secrets import (
    SecretNotFoundError,
    SecretRef,
    SecretRotationOverdueError,
    SecretsProvider,
    scan_for_hardcoded_secrets,
)


def test_get_returns_env_value_for_registered_secret(monkeypatch):
    monkeypatch.setenv("MY_API_KEY", "the-real-value")
    provider = SecretsProvider({"MY_API_KEY": SecretRef(name="MY_API_KEY")})

    assert provider.get("MY_API_KEY") == "the-real-value"


def test_get_unregistered_secret_raises():
    provider = SecretsProvider({})

    with pytest.raises(SecretNotFoundError):
        provider.get("UNKNOWN_KEY")


def test_get_registered_but_unset_secret_raises(monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    provider = SecretsProvider({"MISSING_KEY": SecretRef(name="MISSING_KEY")})

    with pytest.raises(SecretNotFoundError):
        provider.get("MISSING_KEY")


def test_overdue_rotation_raises(monkeypatch):
    monkeypatch.setenv("OLD_KEY", "value")
    old_rotation = datetime.now(timezone.utc) - timedelta(days=200)
    provider = SecretsProvider({"OLD_KEY": SecretRef(name="OLD_KEY", last_rotated_at=old_rotation, rotation_interval_days=90)})

    with pytest.raises(SecretRotationOverdueError):
        provider.get("OLD_KEY")


def test_recent_rotation_does_not_raise(monkeypatch):
    monkeypatch.setenv("FRESH_KEY", "value")
    recent_rotation = datetime.now(timezone.utc) - timedelta(days=5)
    provider = SecretsProvider({"FRESH_KEY": SecretRef(name="FRESH_KEY", last_rotated_at=recent_rotation, rotation_interval_days=90)})

    assert provider.get("FRESH_KEY") == "value"


def test_rotation_enforcement_can_be_disabled(monkeypatch):
    monkeypatch.setenv("OLD_KEY", "value")
    old_rotation = datetime.now(timezone.utc) - timedelta(days=200)
    provider = SecretsProvider(
        {"OLD_KEY": SecretRef(name="OLD_KEY", last_rotated_at=old_rotation, rotation_interval_days=90)},
        enforce_rotation=False,
    )

    assert provider.get("OLD_KEY") == "value"


def test_scan_detects_google_api_key_shape():
    text = 'GEMINI_API_KEY=AIzaSyAhNkvygvNeSBDifXQqVitGS1Mq1xr74CA'

    findings = scan_for_hardcoded_secrets(text)

    assert len(findings) == 1


def test_scan_detects_github_token_shape():
    text = "token: ghp_1234567890abcdef1234567890abcdef1234"

    findings = scan_for_hardcoded_secrets(text)

    assert len(findings) == 1


def test_scan_finds_no_secrets_in_clean_text():
    text = "GEMINI_API_KEY=\nOPENROUTER_API_KEY=\n"

    assert scan_for_hardcoded_secrets(text) == []
