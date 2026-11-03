import logging
from typing import Dict, Optional
from app.config.settings import settings
from app.services.token_service import TokenMetadata, TokenService

logger = logging.getLogger(__name__)


class AuthService:
    """
    Enterprise Authentication Service for ARIIA API interactions.
    Provides centralized bearer token management, scope injection, and an extensible
    framework for future automated OAuth2 token refresh workflows.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        scope_id: Optional[str] = None,
        scope_header_name: Optional[str] = None,
    ):
        self._custom_token = token
        self._custom_scope_id = scope_id
        self.scope_header_name = (
            scope_header_name or settings.ARIIA_SCOPE_HEADER_NAME or "X-Scope-Id"
        )

    def get_token(self) -> Optional[str]:
        """
        Retrieve the active ARIIA bearer access token.
        Falls back to configured settings if no explicit token was passed.
        """
        token = self._custom_token or settings.access_token
        if token:
            clean = token.strip()
            if clean.lower().startswith("bearer "):
                return clean[7:].strip()
            return clean
        return None

    def get_scope_id(self) -> Optional[str]:
        """
        Retrieve the active scope / tenant identifier.
        Checks explicit override, then settings, then decoded token claims.
        """
        if self._custom_scope_id:
            return self._custom_scope_id.strip()

        if settings.scope_id:
            return settings.scope_id.strip()

        # Fallback to inspecting claims in active JWT
        token = self.get_token()
        if token:
            meta = TokenService.decode_token(token)
            if meta.active_scope:
                return meta.active_scope
            if meta.tenant_id:
                return meta.tenant_id

        return None

    def is_token_expired(self) -> bool:
        """
        Check if the currently active token is expired.
        """
        token = self.get_token()
        if not token:
            return True
        return TokenService.is_token_expired(token)

    def get_token_metadata(self) -> TokenMetadata:
        """
        Return decoded token claims and inspection metadata.
        """
        return TokenService.decode_token(self.get_token())

    def get_auth_headers(
        self,
        additional_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Build standardized enterprise HTTP headers including Bearer Authorization,
        application/json content type, and tenant scope headers.

        Returns:
            Dictionary containing Authorization and X-Scope-Id headers if configured.
        """
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "ARIIA-Simulation-Agent/1.0",
        }

        token = self.get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        else:
            logger.debug("[AuthService] No ARIIA_ACCESS_TOKEN available to inject into headers.")

        scope_id = self.get_scope_id()
        if scope_id and self.scope_header_name:
            headers[self.scope_header_name] = scope_id

        if additional_headers:
            headers.update(additional_headers)

        return headers

    async def refresh_token(self) -> Optional[str]:
        """
        Extensible hook for future automated OAuth2 / refresh token exchange.
        Currently returns the static configured token.
        """
        logger.debug("[AuthService] Token refresh requested (extensible framework hook).")
        # Future implementation: post to /api/v1/auth/refresh with refresh_token
        return self.get_token()


# Central singleton
_auth_service_instance: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Retrieve or initialize the centralized AuthService singleton."""
    global _auth_service_instance
    if _auth_service_instance is None:
        _auth_service_instance = AuthService()
    return _auth_service_instance
