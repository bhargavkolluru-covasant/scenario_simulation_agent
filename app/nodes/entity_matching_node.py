import logging

from app.services.entity_matching_service import EntityMatchingService
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def entity_matching_node(state: SimulationState) -> SimulationState:
    """Match the parsed scenario entity against the raw dashboard records."""
    logger.info("[entity_matching_node] Matching scenario entity to dashboard rows")
    state["current_node"] = "entity_matching"

    dashboard_rows = state.get("dashboard_rows", [])
    if not isinstance(dashboard_rows, list):
        dashboard_rows = []

    scenario = state.get("scenario", {})
    target_entity = scenario.get("target_entity", "")
    if not isinstance(target_entity, str) or target_entity == "Unknown Entity":
        target_entity = ""
    if target_entity:
        state["primary_business_entity"] = target_entity

    matched_records = EntityMatchingService().match(
        target_entity,
        dashboard_rows,
    )
    state["matched_dashboard_records"] = matched_records
    state["entity_match_summary"] = {
        "target_entity": target_entity,
        "dashboard_record_count": len(dashboard_rows),
        "matched_record_count": len(matched_records),
        "entity_match_count": len(matched_records),
    }
    if not state.get("primary_business_entity") and target_entity:
        state["primary_business_entity"] = target_entity

    logger.info(
        "[entity_matching_node] Matched %d of %d dashboard rows",
        len(matched_records),
        len(dashboard_rows),
    )
    return state
