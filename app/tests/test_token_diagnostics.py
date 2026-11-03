from datetime import datetime, timezone
import hashlib
import json

import jwt
import pytest

from app.config.settings import settings


def _redact_identifier(value):
    if value is None:
        return None
    text = str(value)
    if len(text) <= 4:
        return "****"
    return f"{text[:2]}...{text[-2:]}"


def token_diagnostics(token):
    """Return allow-listed JWT diagnostics without returning credential material."""
    if not token:
        return {
            "configured": False,
            "token_prefix": "[REDACTED]",
            "token_suffix": "[REDACTED]",
            "is_expired": True,
        }

    clean_token = token.strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()
    try:
        claims = jwt.decode(
            clean_token,
            options={"verify_signature": False, "verify_exp": False},
        )
    except jwt.PyJWTError as exc:
        return {
            "configured": True,
            "token_length": len(clean_token),
            "token_fingerprint": hashlib.sha256(
                clean_token.encode("utf-8")
            ).hexdigest()[:12],
            "token_prefix": "[REDACTED]",
            "token_suffix": "[REDACTED]",
            "decode_error": type(exc).__name__,
            "is_expired": None,
        }

    exp = claims.get("exp")
    iat = claims.get("iat")
    expires_at = (
        datetime.fromtimestamp(exp, timezone.utc).isoformat()
        if isinstance(exp, (int, float))
        else None
    )
    is_expired = (
        exp < datetime.now(timezone.utc).timestamp()
        if isinstance(exp, (int, float))
        else None
    )
    session_id = claims.get("session_id")
    return {
        "configured": True,
        "token_length": len(clean_token),
        "token_fingerprint": hashlib.sha256(
            clean_token.encode("utf-8")
        ).hexdigest()[:12],
        "token_prefix": "[REDACTED]",
        "token_suffix": "[REDACTED]",
        "decoded_claims": {
            "exp": exp,
            "iat": iat,
            "tenant_id": _redact_identifier(claims.get("tenant_id")),
            "active_scope": _redact_identifier(
                claims.get("active_scope") or claims.get("active_scope_id")
            ),
            "session_id": _redact_identifier(session_id),
        },
        "is_expired": is_expired,
        "expires_at": expires_at,
    }


def test_token_diagnostics() -> None:
    diagnostics = token_diagnostics(settings.access_token)
    print(json.dumps(diagnostics, indent=2))
    assert diagnostics["configured"] is bool(settings.access_token)


def test_token_diagnostics_redacts_identifiers_and_token_parts() -> None:
    test_token = jwt.encode(
        {
            "exp": 4_000_000_000,
            "iat": 1_700_000_000,
            "tenant_id": "private-tenant-identifier",
            "active_scope": "private-scope-identifier",
            "session_id": "private-session-identifier",
        },
        "diagnostic-only-test-secret-32-bytes-long",
        algorithm="HS256",
    )
    diagnostics = token_diagnostics(test_token)

    assert diagnostics["decoded_claims"]["exp"] == 4_000_000_000
    assert diagnostics["decoded_claims"]["iat"] == 1_700_000_000
    assert diagnostics["is_expired"] is False
    assert diagnostics["token_prefix"] == "[REDACTED]"
    assert diagnostics["token_suffix"] == "[REDACTED]"
    assert "private-session-identifier" not in json.dumps(diagnostics)
