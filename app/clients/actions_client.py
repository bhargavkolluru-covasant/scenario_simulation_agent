import logging
from typing import Any, Dict, List, Optional

from app.clients.base_client import BaseClient
from app.config.settings import settings

logger = logging.getLogger(__name__)


class ActionsClient(BaseClient):
    """Client for ARIIA Platform recommended actions and action metrics."""

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
            or settings.ACTIONS_URL
        )
        super().__init__(
            base_url=settings.get_service_url(resolved_url),
            timeout=timeout or settings.API_TIMEOUT,
            auth_token=auth_token,
            enterprise_id=enterprise_id,
            domain_ids=domain_ids,
            scope_id=scope_id,
        )

    async def get_actions(self) -> List[Dict[str, Any]]:
        logger.info("[ActionsClient] Fetching recommended actions")
        response = await self.get("/api/v1/metrics/insights/actions")
        if not isinstance(response, (dict, list)):
            raise TypeError("Actions API response must be a JSON object or list.")

        records = self._find_action_records(response)
        if records is None:
            raise TypeError("Actions API response did not contain an actions list.")
        if not isinstance(records, list) or not all(
            isinstance(action, dict) for action in records
        ):
            raise TypeError("Actions API response must contain a list of action objects.")
        return records

    @classmethod
    def _find_action_records(cls, payload: Any) -> Optional[List[Any]]:
        if isinstance(payload, list):
            if all(isinstance(item, dict) for item in payload):
                return payload
            return None
        if isinstance(payload, dict):
            for key, value in payload.items():
                if key.lower() in {
                    "actions",
                    "recommended_actions",
                    "recommendations",
                    "items",
                    "results",
                    "data",
                }:
                    if isinstance(value, list):
                        return value
                    nested = cls._find_action_records(value)
                    if nested is not None:
                        return nested
            for value in payload.values():
                nested = cls._find_action_records(value)
                if nested is not None:
                    return nested
        return None

    async def get_action_stats(self) -> Dict[str, Any]:
        logger.info("[ActionsClient] Fetching action statistics")
        response = await self.get("/api/v1/metrics/actions-stats")
        if not isinstance(response, dict):
            raise TypeError("Action stats API response must be a JSON object.")
        return response
