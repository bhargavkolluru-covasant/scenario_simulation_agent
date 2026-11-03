import logging
from typing import Any, Dict, List, Optional

from app.clients.base_client import BaseClient
from app.config.settings import settings

logger = logging.getLogger(__name__)


class KPIInsightsClient(BaseClient):
    """Client for ARIIA Platform KPI insight data."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        auth_token: Optional[str] = None,
        enterprise_id: Optional[str] = None,
        domain_ids: Optional[List[str]] = None,
        scope_id: Optional[str] = None,
    ):
        resolved_url = (
            base_url
            or settings.KPI_INSIGHTS_URL
        )
        super().__init__(
            base_url=settings.get_service_url(resolved_url),
            timeout=timeout or settings.API_TIMEOUT,
            auth_token=auth_token,
            enterprise_id=enterprise_id,
            domain_ids=domain_ids,
            scope_id=scope_id,
        )

    async def get_kpis(self) -> Any:
        logger.info("[KPIInsightsClient] Fetching KPI insights")
        response = await self.get("/api/v1/metrics/insights/kpis")
        if not isinstance(response, (dict, list)):
            raise TypeError("KPI insights API response must be a JSON object or list.")
        return response

    async def get_insights_stats(self) -> Dict[str, Any]:
        logger.info("[KPIInsightsClient] Fetching KPI insight statistics")
        response = await self.get("/api/v1/metrics/insights-stats")
        if not isinstance(response, dict):
            raise TypeError("KPI insight stats API response must be a JSON object.")
        return response
