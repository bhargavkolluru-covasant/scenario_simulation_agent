import logging
from typing import Any, Dict, Optional
from app.clients.base_client import BaseClient
from app.config.settings import settings

logger = logging.getLogger(__name__)


class VendorClient(BaseClient):
    """
    Client for Vendor Service.
    Retrieves vendor profiles, supplier risk scores, risk details, and organizational hierarchy.
    Endpoints:
      - GET /api/v1/vendors
      - GET /api/v1/vendors/{vendor_id}
      - GET /api/v1/vendors/{vendor_id}/risk-score
      - GET /api/v1/vendors/{vendor_id}/hierarchy
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        resolved_url = settings.get_service_url(base_url or settings.VENDOR_SERVICE_URL)
        super().__init__(
            base_url=resolved_url,
            timeout=timeout or settings.API_TIMEOUT,
        )

    async def get_vendors(
        self,
        limit: int = 100,
        force_recalculate: bool = False,
    ) -> Dict[str, Any]:
        """Fetch list of vendors with aggregated risk scores."""
        logger.info(f"[VendorClient] Fetching vendors (limit={limit}, force_recalculate={force_recalculate})")
        return await self.get(
            "/api/v1/vendors",
            params={"limit": limit, "force_recalculate": force_recalculate},
        )

    async def get_vendor_detail(
        self,
        vendor_id: str,
        include_cyber: bool = True,
    ) -> Dict[str, Any]:
        """Get comprehensive risk detail and metrics for a specific vendor."""
        logger.info(f"[VendorClient] Fetching vendor details for {vendor_id}")
        return await self.get(
            f"/api/v1/vendors/{vendor_id}",
            params={"include_cyber": include_cyber},
        )

    async def get_vendor_risk_score(self, vendor_id: str) -> Dict[str, Any]:
        """Get isolated risk score and component ratings for a specific vendor."""
        logger.info(f"[VendorClient] Fetching risk score for vendor {vendor_id}")
        return await self.get(f"/api/v1/vendors/{vendor_id}/risk-score")

    async def get_vendor_hierarchy(self, vendor_id: str) -> Dict[str, Any]:
        """Get parent-child corporate hierarchy for a vendor."""
        logger.info(f"[VendorClient] Fetching hierarchy for vendor {vendor_id}")
        return await self.get(f"/api/v1/vendors/{vendor_id}/hierarchy")
