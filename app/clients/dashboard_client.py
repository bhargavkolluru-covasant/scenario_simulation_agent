import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from app.clients.base_client import BaseClient
from app.config.settings import settings

logger = logging.getLogger(__name__)


class DashboardClient(BaseClient):
    """
    Client for ARIIA Platform Dashboard APIs.

    Uses:

    GET /api/v1/dashboards/{dashboard_id}/data

    as the primary source of business intelligence.

    The dashboard definition endpoint is optional because
    some ARIIA environments do not expose:

    GET /api/v1/dashboards/{dashboard_id}
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
        resolved_url = (
            base_url
            or settings.DASHBOARD_URL
            or settings.PLATFORM_BACKEND_URL
        )

        super().__init__(
            base_url=settings.get_service_url(
                resolved_url
            ),
            timeout=timeout
            or settings.API_TIMEOUT,
            auth_token=auth_token,
            enterprise_id=enterprise_id,
            domain_ids=domain_ids,
            scope_id=scope_id,
        )

    async def get_dashboard(
        self,
        dashboard_id: str,
    ) -> Dict[str, Any]:
        """
        Dashboard definition lookup.

        This endpoint is optional and some deployments
        return HTTP 404.

        Never fail the workflow because of a missing
        dashboard definition.
        """

        if (
            not dashboard_id
            or not dashboard_id.strip()
        ):
            raise ValueError(
                "dashboard_id is required."
            )

        encoded_dashboard_id = quote(
            dashboard_id.strip(),
            safe=""
        )

        try:

            logger.info(
                "[DashboardClient] "
                "Fetching dashboard definition"
            )

            response = await self.get(
                f"/api/v1/dashboards/"
                f"{encoded_dashboard_id}"
            )

            if not isinstance(
                response,
                dict
            ):
                raise TypeError(
                    "Dashboard definition "
                    "response must be JSON."
                )

            return response

        except Exception as exc:

            logger.warning(
                "[DashboardClient] "
                f"Dashboard definition "
                f"lookup unavailable: {exc}"
            )

            return {}

    async def get_dashboard_data(
        self,
        dashboard_id: str,
    ) -> Dict[str, Any]:
        """
        Primary dashboard data endpoint.

        This endpoint is the authoritative source
        of dashboard intelligence and MUST succeed.
        """

        if (
            not dashboard_id
            or not dashboard_id.strip()
        ):
            raise ValueError(
                "dashboard_id is required."
            )

        encoded_dashboard_id = quote(
            dashboard_id.strip(),
            safe=""
        )

        logger.info(
            "[DashboardClient] "
            "Fetching dashboard data"
        )

        response = await self.get(
            f"/api/v1/dashboards/"
            f"{encoded_dashboard_id}/data"
        )

        if not isinstance(
            response,
            dict
        ):
            raise TypeError(
                "Dashboard data "
                "response must be JSON."
            )

        return response

    async def get_dashboard_context(
        self,
        dashboard_id: str,
    ) -> Dict[str, Any]:
        """
        Unified method used by dashboard node.

        Always returns:

        {
            "data": ...,
            "definition": ...
        }

        even if definition endpoint is unavailable.
        """

        data = await self.get_dashboard_data(
            dashboard_id
        )

        definition = (
            await self.get_dashboard(
                dashboard_id
            )
        )

        return {
            "data": data,
            "definition": definition,
        }