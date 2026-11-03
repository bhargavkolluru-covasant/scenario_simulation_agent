import logging
from typing import Any, Dict, Optional
from app.clients.base_client import BaseClient
from app.config.settings import settings

logger = logging.getLogger(__name__)


class MarketRiskClient(BaseClient):
    """
    Client for Market Risk Service.
    Retrieves FX currency exposure, risk distribution, market volatility risk scores, and risk cases.
    Endpoints:
      - GET /api/v1/market-risk/fx-exposure
      - GET /api/v1/market-risk/risk-distribution
      - GET /api/v1/market-risk/currency-risk-score
      - GET /api/v1/market-risk/cases
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        resolved_url = settings.get_service_url(base_url or settings.MARKET_RISK_SERVICE_URL)
        super().__init__(
            base_url=resolved_url,
            timeout=timeout or settings.API_TIMEOUT,
        )

    async def get_fx_exposure(
        self,
        vendor_id: Optional[str] = None,
        currency: Optional[str] = None,
        risk_level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Fetch FX exposure summary and individual currency position exposures."""
        params = {
            "vendor_id": vendor_id,
            "currency": currency,
            "risk_level": risk_level,
            "limit": limit,
            "offset": offset,
        }
        logger.info(f"[MarketRiskClient] Fetching FX exposure (currency={currency}, risk_level={risk_level})")
        return await self.get("/api/v1/market-risk/fx-exposure", params=params)

    async def get_risk_distribution(self) -> Dict[str, Any]:
        """Fetch market risk distribution and percentage breakdowns."""
        logger.info("[MarketRiskClient] Fetching market risk distribution")
        return await self.get("/api/v1/market-risk/risk-distribution")

    async def get_currency_risk_score(self) -> Dict[str, Any]:
        """Fetch aggregated currency risk score and volatility trend indicators."""
        logger.info("[MarketRiskClient] Fetching currency risk score")
        return await self.get("/api/v1/market-risk/currency-risk-score")

    async def get_cases(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Fetch active market risk cases and identified anomalies."""
        params = {
            "status": status,
            "severity": severity,
            "limit": limit,
        }
        logger.info(f"[MarketRiskClient] Fetching market risk cases (status={status}, severity={severity})")
        return await self.get("/api/v1/market-risk/cases", params=params)
