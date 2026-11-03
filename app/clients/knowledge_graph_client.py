import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from app.clients.base_client import BaseClient
from app.config.settings import settings

logger = logging.getLogger(__name__)


class KnowledgeGraphClient(BaseClient):
    """
    Client for Knowledge Graph Service.
    Enables relationship discovery, graph traversal, dependency inspection, and entity enrichment.
    Endpoints:
      - GET /api/v1/data-management/knowledge-graph
      - GET /api/v1/data-management/knowledge-graph/stats
      - GET /api/v1/data-management/knowledge-graph/node/{node_id}
      - GET /api/v1/data-management/knowledge-graph/entities/{node_type}
      - GET /api/v1/data-management/knowledge-graph/subgraph/{node_id}
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
            base_url or settings.KNOWLEDGE_GRAPH_URL or settings.PLATFORM_BACKEND_URL
        )
        super().__init__(
            base_url=resolved_url,
            timeout=timeout or settings.API_TIMEOUT,
            auth_token=auth_token,
            enterprise_id=enterprise_id,
            domain_ids=domain_ids,
            scope_id=scope_id,
        )

    async def get_graph(
        self,
        node_type: Optional[str] = None,
        relationship_type: Optional[str] = None,
        limit: int = 100,
        include_stats: bool = True,
        tier: str = "tables",
    ) -> Dict[str, Any]:
        """Fetch knowledge graph nodes and edges with optional filtering."""
        params = {
            "node_type": node_type,
            "relationship_type": relationship_type,
            "limit": limit,
            "include_stats": include_stats,
            "tier": tier,
        }
        logger.info(f"[KnowledgeGraphClient] Querying graph (node_type={node_type}, limit={limit})")
        return await self.get("/api/v1/data-management/knowledge-graph", params=params)

    async def get_knowledge_graph(
        self,
        node_type: Optional[str] = None,
        relationship_type: Optional[str] = None,
        limit: int = 100,
        include_stats: bool = True,
        tier: str = "tables",
    ) -> Dict[str, Any]:
        """Backward-compatible alias for :meth:`get_graph`."""
        return await self.get_graph(
            node_type=node_type,
            relationship_type=relationship_type,
            limit=limit,
            include_stats=include_stats,
            tier=tier,
        )

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics regarding nodes, relationship counts, and types."""
        logger.info("[KnowledgeGraphClient] Fetching knowledge graph stats")
        return await self.get("/api/v1/data-management/knowledge-graph/stats")

    async def get_node(self, node_id: str, depth: int = 1) -> Dict[str, Any]:
        """Fetch details of a specific node and its immediate relationships."""
        if not node_id or not node_id.strip():
            raise ValueError("node_id must be a non-empty string")
        logger.info(f"[KnowledgeGraphClient] Fetching node {node_id} with depth {depth}")
        return await self.get(
            f"/api/v1/data-management/knowledge-graph/node/{quote(node_id.strip(), safe='')}",
            params={"depth": depth},
        )

    async def get_entities(self, node_type: str, limit: int = 1000) -> Any:
        """Return lightweight list of entities matching a specific node type."""
        if not node_type or not node_type.strip():
            raise ValueError("node_type must be a non-empty string")
        logger.info(f"[KnowledgeGraphClient] Fetching entities for type: {node_type}")
        return await self.get(
            f"/api/v1/data-management/knowledge-graph/entities/{quote(node_type.strip(), safe='')}",
            params={"limit": limit},
        )

    async def get_entities_by_type(self, node_type: str, limit: int = 1000) -> Any:
        """Backward-compatible alias for :meth:`get_entities`."""
        return await self.get_entities(node_type=node_type, limit=limit)

    async def get_subgraph(self, node_id: str, limit: int = 50) -> Dict[str, Any]:
        """Return a subgraph centered on a specific node with direct neighbors and edges."""
        if not node_id or not node_id.strip():
            raise ValueError("node_id must be a non-empty string")
        logger.info(f"[KnowledgeGraphClient] Fetching subgraph for node: {node_id}")
        return await self.get(
            f"/api/v1/data-management/knowledge-graph/subgraph/{quote(node_id.strip(), safe='')}",
            params={"limit": limit},
        )
