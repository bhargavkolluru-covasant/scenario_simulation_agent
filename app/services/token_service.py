from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
import jwt
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TokenMetadata(BaseModel):
    """
    Decoded metadata and claims from an ARIIA JWT Bearer token.
    Extracted without cryptographic verification for client-side inspection.
    """
    sub: Optional[str] = Field(default=None, description="Subject identifier (user/service ID)")
    email: Optional[str] = Field(default=None, description="User email address")
    exp: Optional[int] = Field(default=None, description="Expiration UNIX timestamp")
    tenant_id: Optional[str] = Field(default=None, description="Tenant/Organization ID")
    active_scope: Optional[str] = Field(default=None, description="Active operational scope ID")
    is_expired: bool = Field(default=False, description="True if exp timestamp is in the past")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration formatted as UTC datetime")
    raw_payload: Dict[str, Any] = Field(default_factory=dict, description="Complete unverified claims payload")


class TokenService:
    """
    Enterprise token inspection service using PyJWT.
    Decodes tokens without verification to inspect expiration, tenant context, and active scopes.
    """

    @classmethod
    def decode_token(cls, token: Optional[str]) -> TokenMetadata:
        """
        Decode a JWT without cryptographic verification and extract standard claims.

        Args:
            token: Raw JWT string or 'Bearer <token>'.

        Returns:
            TokenMetadata with extracted claims and expiration status.
        """
        if not token or not isinstance(token, str):
            logger.debug("[TokenService] Empty or non-string token provided.")
            return TokenMetadata(is_expired=True)

        clean_token = token.strip()
        if clean_token.lower().startswith("bearer "):
            clean_token = clean_token[7:].strip()

        if not clean_token:
            return TokenMetadata(is_expired=True)

        try:
            payload: Dict[str, Any] = jwt.decode(
                clean_token,
                options={"verify_signature": False, "verify_exp": False},
            )
        except Exception as exc:
            logger.warning(f"[TokenService] Failed to decode JWT payload: {exc}")
            return TokenMetadata(is_expired=True, raw_payload={"error": str(exc)})

        # Extract standard claims with flexible key lookups
        sub = payload.get("sub")
        email = payload.get("email") or payload.get("user_email")
        exp = payload.get("exp")
        tenant_id = (
            payload.get("tenant_id")
            or payload.get("tenant")
            or payload.get("org_id")
        )
        active_scope = (
            payload.get("active_scope")
            or payload.get("scope_id")
            or payload.get("active_scope_id")
            or payload.get("scope")
        )

        is_expired = False
        expires_at: Optional[datetime] = None
        if exp is not None:
            try:
                expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
                now_utc = datetime.now(timezone.utc)
                is_expired = expires_at < now_utc
            except Exception as e:
                logger.debug(f"[TokenService] Error computing expiration datetime: {e}")
                is_expired = True

        return TokenMetadata(
            sub=str(sub) if sub is not None else None,
            email=str(email) if email is not None else None,
            exp=int(exp) if isinstance(exp, (int, float)) else None,
            tenant_id=str(tenant_id) if tenant_id is not None else None,
            active_scope=str(active_scope) if active_scope is not None else None,
            is_expired=is_expired,
            expires_at=expires_at,
            raw_payload=payload,
        )

    @classmethod
    def is_token_expired(cls, token: Optional[str]) -> bool:
        """
        Quickly check whether a JWT has expired without verifying signature.
        """
        metadata = cls.decode_token(token)
        return metadata.is_expired
