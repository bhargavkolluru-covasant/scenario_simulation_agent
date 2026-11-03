import logging
from typing import Any, Dict, Optional
from app.clients.base_client import BaseClient
from app.config.settings import settings

logger = logging.getLogger(__name__)


class InvoiceClient(BaseClient):
    """
    Client for Invoice Service.
    Retrieves invoice records, payment status, financial liability, and aggregate stats.
    Endpoints:
      - GET /api/v1/invoices
      - GET /api/v1/invoices/{invoice_id}
      - GET /api/v1/invoices/stats
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        resolved_url = settings.get_service_url(base_url or settings.INVOICE_SERVICE_URL)
        super().__init__(
            base_url=resolved_url,
            timeout=timeout or settings.API_TIMEOUT,
        )

    async def get_invoices(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List invoices with risk flags, payment status, and PO linkage."""
        params = {
            "limit": limit,
            "offset": offset,
            "status": status,
            "risk_level": risk_level,
            "search": search,
        }
        logger.info(f"[InvoiceClient] Fetching invoices (limit={limit}, status={status})")
        return await self.get("/api/v1/invoices", params=params)

    async def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Get granular detail for an invoice including vendor profile and payment trace."""
        logger.info(f"[InvoiceClient] Fetching invoice {invoice_id}")
        return await self.get(f"/api/v1/invoices/{invoice_id}")

    async def get_invoice_stats(self) -> Dict[str, Any]:
        """Get aggregate invoice financial stats (outstanding amount, overdue count, etc.)."""
        logger.info("[InvoiceClient] Fetching invoice statistics")
        return await self.get("/api/v1/invoices/stats")
