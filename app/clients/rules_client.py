import logging
from typing import Any, Dict, List, Optional
from app.clients.base_client import BaseClient
from app.config.settings import settings

logger = logging.getLogger(__name__)


class RulesClient(BaseClient):
    """
    Client for Rules Service.
    Retrieves business rules, entity-specific rules, domain agent rules, and natural-language explanations.
    Endpoints:
      - GET /api/v1/rules
      - GET /api/v1/rules/{rule_id}
      - GET /api/v1/rules/{rule_id}/explain
      - GET /api/v1/rules/entity/{entity_type}
      - GET /api/v1/rules/agent/{agent_name}
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        auth_token: Optional[str] = None,
        enterprise_id: Optional[str] = None,
        domain_ids: Optional[List[str]] = None,
        scope_id: Optional[str] = None,
    ):
        resolved_url = settings.get_service_url(
            base_url or settings.RULES_SERVICE_URL or settings.PLATFORM_BACKEND_URL
        )
        super().__init__(
            base_url=resolved_url,
            timeout=timeout or settings.API_TIMEOUT,
            auth_token=auth_token,
            enterprise_id=enterprise_id,
            domain_ids=domain_ids,
            scope_id=scope_id,
        )

    async def get_rules(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        rule_type: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """List enterprise business risk rules with optional attribute filtering."""
        params = {
            "category": category,
            "status": status,
            "severity": severity,
            "rule_type": rule_type,
            "limit": limit,
        }
        logger.info(f"[RulesClient] Fetching rules (category={category}, status={status}, limit={limit})")
        return await self.get("/api/v1/rules", params=params)

    async def get_rule(self, rule_id: str) -> Dict[str, Any]:
        """Fetch specification and executable logic of a specific rule by ID."""
        logger.info(f"[RulesClient] Fetching rule details for {rule_id}")
        return await self.get(f"/api/v1/rules/{rule_id}")

    async def explain_rule(self, rule_id: str) -> Dict[str, Any]:
        """Get human-readable AI explanation and logic breakdown for a rule."""
        logger.info(f"[RulesClient] Explaining rule {rule_id}")
        return await self.get(f"/api/v1/rules/{rule_id}/explain")

    async def get_rules_for_entity(self, entity_type: str) -> Dict[str, Any]:
        """Get all active risk rules applicable to a specific entity type."""
        logger.info(f"[RulesClient] Fetching rules for entity type: {entity_type}")
        return await self.get(f"/api/v1/rules/entity/{entity_type}")

    async def get_rules_by_agent(
        self,
        agent_name: str,
        include_inactive: bool = False,
    ) -> Dict[str, Any]:
        """Get all rules assigned to a specific domain agent."""
        logger.info(f"[RulesClient] Fetching rules for agent: {agent_name}")
        return await self.get(
            f"/api/v1/rules/agent/{agent_name}",
            params={"include_inactive": include_inactive},
        )
