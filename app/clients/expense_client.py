import logging
from typing import Any, Dict, Optional
from app.clients.base_client import BaseClient
from app.config.settings import settings

logger = logging.getLogger(__name__)


class ExpenseClient(BaseClient):
    """
    Client for Expense Service.
    Retrieves corporate employee expenses, department spend patterns, and anomaly stats.
    Endpoints:
      - GET /api/v1/expenses
      - GET /api/v1/expenses/{expense_id}
      - GET /api/v1/expenses/stats
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        resolved_url = settings.get_service_url(base_url or settings.EXPENSE_SERVICE_URL)
        super().__init__(
            base_url=resolved_url,
            timeout=timeout or settings.API_TIMEOUT,
        )

    async def get_expenses(
        self,
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        department: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch paginated list of corporate expenses with merchant and department metadata."""
        params = {
            "page": page,
            "page_size": page_size,
            "status": status,
            "risk_level": risk_level,
            "department": department,
            "search": search,
        }
        logger.info(f"[ExpenseClient] Fetching expenses (page={page}, page_size={page_size})")
        return await self.get("/api/v1/expenses", params=params)

    async def get_expense(self, expense_id: str) -> Dict[str, Any]:
        """Fetch granular information for a specific expense transaction."""
        logger.info(f"[ExpenseClient] Fetching expense {expense_id}")
        return await self.get(f"/api/v1/expenses/{expense_id}")

    async def get_expense_stats(self) -> Dict[str, Any]:
        """Get aggregated expense metrics, high-risk spend, and category breakdown."""
        logger.info("[ExpenseClient] Fetching expense statistics")
        return await self.get("/api/v1/expenses/stats")
