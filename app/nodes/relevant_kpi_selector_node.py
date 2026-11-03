import logging

from app.services.dashboard_intelligence_service import select_relevant_kpis
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def relevant_kpi_selector_node(state: SimulationState) -> SimulationState:
    """
    Node 3: Relevant KPI Selector
    Builds dashboard-scoped KPI pool and ranks candidate KPIs using:
    Dashboard (25%) + Scenario (25%) + Entity (20%) + Semantic (20%) + Confidence (10%).
    Enforces PRIMARY KPI RULE: Selects 1 Primary KPI and 2 Supporting KPIs.
    """
    logger.info(
        "[relevant_kpi_selector_node] Selecting KPIs using "
        "dashboard/scenario/entity/semantic/confidence relevance"
    )
    state["current_node"] = "relevant_kpi_selector"

    selection = select_relevant_kpis(state)

    state["dashboard_kpi_records"] = selection["dashboard_kpi_records"]
    state["selected_dashboard_kpi_names"] = selection["selected_dashboard_kpi_names"]
    state["allowed_kpi_terms"] = selection["allowed_kpi_terms"]
    state["strict_dashboard_filter"] = selection["strict_dashboard_filter"]
    state["primary_kpi"] = selection.get("primary_kpi")
    state["supporting_kpis"] = selection.get("supporting_kpis") or []

    logger.info(
        "[relevant_kpi_selector_node] Selected %d dashboard KPI records; Primary KPI: %s, Supporting: %s",
        len(selection["dashboard_kpi_records"]),
        (selection.get("primary_kpi") or {}).get("name"),
        [k.get("name") for k in (selection.get("supporting_kpis") or [])],
    )
    return state


class RelevantKPISelectorNode:
    """Class wrapper for backward compatibility."""

    async def execute(self, state: SimulationState) -> SimulationState:
        return await relevant_kpi_selector_node(state)
