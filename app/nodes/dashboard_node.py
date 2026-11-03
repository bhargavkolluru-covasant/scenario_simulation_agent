import logging
from typing import Any, Dict, List

from app.clients.dashboard_client import DashboardClient
from app.config.settings import settings
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


def _extract_widget_rows(payload: Any) -> List[Any]:
    rows: List[Any] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():

                if key == "widgets" and isinstance(
                    child,
                    list,
                ):
                    for widget in child:

                        if not isinstance(
                            widget,
                            dict,
                        ):
                            continue

                        data = widget.get(
                            "data"
                        )

                        if (
                            isinstance(
                                data,
                                dict,
                            )
                            and isinstance(
                                data.get(
                                    "rows"
                                ),
                                list,
                            )
                        ):
                            rows.extend(
                                data["rows"]
                            )

                else:
                    visit(child)

        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload)

    return rows


def _extract_widget_kpis(
    payload: Any,
) -> List[Dict[str, Any]]:
    """
    Extract KPI candidates directly
    from dashboard widget titles.

    Example:
        DLD Price PSF Trend
        Competitor Launches by Detection Source
        Upcoming Supply
        Avg News Sentiment (30d)
    """

    kpis: List[Dict[str, Any]] = []

    if not isinstance(payload, dict):
        return kpis

    widgets = payload.get(
        "widgets",
        [],
    )

    if not isinstance(
        widgets,
        list,
    ):
        return kpis

    seen = set()

    for widget in widgets:

        if not isinstance(
            widget,
            dict,
        ):
            continue

        title = str(
            widget.get(
                "title",
                ""
            )
        ).strip()

        if not title:
            continue

        identity = (
            title.casefold()
        )

        if identity in seen:
            continue

        seen.add(identity)

        kpis.append(
            {
                "name": title,
                "source": "widget_title",
                "dashboard_evidence": True,
            }
        )

    return kpis


async def dashboard_node(
    state: SimulationState,
) -> SimulationState:
    """
    Load dashboard intelligence.

    Populates:

    - dashboard_data
    - dashboard_definition
    - dashboard_rows
    - dashboard_widget_kpis
    """

    logger.info(
        "[dashboard_node] Loading dashboard intelligence"
    )

    state[
        "current_node"
    ] = "dashboard_intelligence"

    dashboard_id = (
        state.get(
            "dashboard_id"
        )
        or settings.DASHBOARD_ID
    )

    if not dashboard_id:
        raise ValueError(
            "DASHBOARD_ID must be configured."
        )

    client = DashboardClient(
        auth_token=state.get(
            "access_token"
        ),
        enterprise_id=state.get(
            "enterprise_id"
        ),
        domain_ids=state.get(
            "domain_ids"
        ),
        scope_id=state.get(
            "scope_id"
        ),
    )

    dashboard_context = (
        await client.get_dashboard_context(
            dashboard_id
        )
    )

    logger.info(
        "[DEBUG] dashboard_id=%s",
        dashboard_id,
    )

    logger.info(
        "[DEBUG] dashboard_name=%s",
        (
            dashboard_context.get(
                "definition",
                {},
            ).get("name")
            or dashboard_context.get(
                "data",
                {},
            ).get("name")
        ),
    )

    payload = (
        dashboard_context.get(
            "data",
            {},
        )
    )

    definition = (
        dashboard_context.get(
            "definition",
            {},
        )
    )

    if (
        not isinstance(payload, dict)
        or not isinstance(
            definition,
            dict,
        )
    ):
        raise TypeError(
            "Dashboard context data and definition must be objects."
        )

    rows = _extract_widget_rows(
        payload
    )

    widget_kpis = (
        _extract_widget_kpis(
            payload
        )
    )

    state["dashboard_id"] = (
        dashboard_id
    )

    state["dashboard_data"] = (
        payload
    )

    state["dashboard_definition"] = (
        definition
    )

    state["dashboard_rows"] = (
        rows
    )

    state["dashboard_widget_kpis"] = (
        widget_kpis
    )

    logger.info(
        "[dashboard_node] Loaded %d dashboard rows",
        len(rows),
    )

    logger.info(
        "[dashboard_node] Extracted %d widget KPI candidates",
        len(widget_kpis),
    )

    logger.info(
        "[dashboard_node] Widget KPIs=%s",
        [
            k["name"]
            for k in widget_kpis[:10]
        ],
    )

    return state