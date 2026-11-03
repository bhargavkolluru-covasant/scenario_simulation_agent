import logging
from typing import Dict, List, Optional

from app.config.settings import settings
from app.services.auth_service import get_auth_service

logger = logging.getLogger(__name__)


class ContextInitializationError(Exception):
    """Raised when execution context cannot be initialized."""


class ContextService:
    """
    Enterprise Context Service.

    Responsibilities:
    - Initialize execution context
    - Resolve enterprise and domain context
    - Retain optional legacy scope support
    - Build reusable downstream context
    - Provide a single source of truth
      for workflow execution context
    """

    def __init__(
        self,
        scope_id: Optional[str] = None,
        enterprise_id: Optional[str] = None,
        domain_ids: Optional[List[str]] = None,
    ):
        self._scope_id = scope_id
        self._enterprise_id = enterprise_id
        self._domain_ids = domain_ids
        self._auth_service = get_auth_service()

    def get_enterprise_id(self) -> str:
        enterprise_id = self._enterprise_id or settings.enterprise_id
        if not enterprise_id:
            raise ContextInitializationError(
                "No active ARIIA enterprise is configured."
            )
        return enterprise_id.strip()

    def get_domain_ids(self) -> List[str]:
        domain_ids = self._domain_ids or settings.domain_ids
        if not domain_ids:
            raise ContextInitializationError(
                "No active ARIIA domains are configured."
            )
        return [domain.strip() for domain in domain_ids if domain.strip()]

    def get_scope_id(self) -> str:
        """
        Resolve legacy scope in the following order:

        1. Explicit scope passed to service
        2. Settings scope
        3. JWT active_scope claim
        """

        if self._scope_id:
            return self._scope_id.strip()

        scope = self._auth_service.get_scope_id()

        if scope:
            return str(scope)

        raise ContextInitializationError(
            "No active ARIIA scope available."
        )

    def initialize_context(self) -> Dict:
        """
        Build execution context.
        """

        enterprise_id = self.get_enterprise_id()
        domain_ids = self.get_domain_ids()
        try:
            scope_id = self.get_scope_id()
        except ContextInitializationError:
            scope_id = ""

        context = {
            "enterprise_id": enterprise_id,
            "domain_ids": domain_ids,
            "scope_id": scope_id,
        }

        logger.info(
            "[ContextService] Context initialized for enterprise=%s domains=%s",
            enterprise_id,
            domain_ids,
        )

        return context


_context_service_instance = None


def get_context_service():
    global _context_service_instance

    if _context_service_instance is None:
        _context_service_instance = ContextService()

    return _context_service_instance