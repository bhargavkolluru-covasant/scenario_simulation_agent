import logging
from typing import Any, Dict, Optional
from app.clients.base_client import BaseClient
from app.config.settings import settings

logger = logging.getLogger(__name__)


class ProcurementClient(BaseClient):
    """
    Client for Procurement Service.
    Retrieves purchase orders, procurement stats, trends, and supply chain operational data.
    Endpoints:
      - GET /api/v1/procurement/purchase-orders
      - GET /api/v1/procurement/purchase-orders/{po_id}
      - GET /api/v1/procurement/stats
      - GET /api/v1/procurement/trends
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        resolved_url = settings.get_service_url(base_url or settings.PROCUREMENT_SERVICE_URL)
        super().__init__(
            base_url=resolved_url,
            timeout=timeout or settings.API_TIMEOUT,
        )

    async def get_purchase_orders(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        department: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch list of purchase orders with enriched supplier and contract data."""
        params = {
            "limit": limit,
            "offset": offset,
            "status": status,
            "risk_level": risk_level,
            "department": department,
            "search": search,
        }
        logger.info(f"[ProcurementClient] Fetching purchase orders (limit={limit}, status={status})")
        return await self.get("/api/v1/procurement/purchase-orders", params=params)

    async def get_purchase_order(self, po_id: str) -> Dict[str, Any]:
        """Fetch full details for a specific purchase order including contracts and line items."""
        logger.info(f"[ProcurementClient] Fetching purchase order {po_id}")
        return await self.get(f"/api/v1/procurement/purchase-orders/{po_id}")

    async def get_procurement_stats(self) -> Dict[str, Any]:
        """Get aggregated procurement KPIs and statistical counts."""
        logger.info("[ProcurementClient] Fetching procurement statistics")
        return await self.get("/api/v1/procurement/stats")

    async def get_procurement_trends(self, period_days: int = 30) -> Dict[str, Any]:
        """Get procurement trend time-series data for analysis."""
        logger.info(f"[ProcurementClient] Fetching procurement trends (period_days={period_days})")
        return await self.get(
            "/api/v1/procurement/trends",
            params={"period_days": period_days},
        )
