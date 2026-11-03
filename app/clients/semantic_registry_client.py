import logging
from typing import Any, Dict, List, Optional
from app.clients.base_client import BaseClient
from app.config.settings import settings

logger = logging.getLogger(__name__)


class SemanticRegistryClient(BaseClient):
    """
    Client for Semantic Registry Service.
    Discovers business entities, attributes, and assists in canonical entity modeling.
    Endpoints:
      - GET /api/v1/data-management/semantic-registry
      - GET /api/v1/data-management/semantic-registry/entities
      - GET /api/v1/data-management/semantic-registry/entities/{entity_name}
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        resolved_url = settings.get_service_url(base_url or settings.SEMANTIC_REGISTRY_URL)
        super().__init__(
            base_url=resolved_url,
            timeout=timeout or settings.API_TIMEOUT,
        )

    async def get_semantic_registry(self) -> Dict[str, Any]:
        """Fetch the full semantic registry including metadata and entities."""
        logger.info("[SemanticRegistryClient] Fetching full semantic registry")
        return await self.get("/api/v1/data-management/semantic-registry")

    async def get_entities(self) -> List[Any]:
        """List all entity names registered in the semantic registry."""
        logger.info("[SemanticRegistryClient] Fetching semantic entity names")
        return await self.get("/api/v1/data-management/semantic-registry/entities")

    async def get_entity(self, entity_name: str) -> Dict[str, Any]:
        """Fetch full details and schema for a specific semantic entity."""
        logger.info(f"[SemanticRegistryClient] Fetching entity details for: {entity_name}")
        return await self.get(f"/api/v1/data-management/semantic-registry/entities/{entity_name}")
