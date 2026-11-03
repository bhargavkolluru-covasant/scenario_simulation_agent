import logging
from typing import Any, Dict, List
from app.clients.rules_client import RulesClient
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def rules_node(state: SimulationState) -> SimulationState:
    """
    LangGraph Node: Business Rules Discovery
    Loads applicable business rules, governance constraints, and rule explanations.
    """
    logger.info("[rules_node] Loading business rules")
    state["current_node"] = "rules"
    client = RulesClient(
        auth_token=state.get("access_token"),
        enterprise_id=state.get("enterprise_id"),
        domain_ids=state.get("domain_ids"),
        scope_id=state.get("scope_id"),
    )

    try:
        rules_response = await client.get_rules(limit=100)
        rules_list = rules_response.get("rules", [])

        if not isinstance(rules_list, list):
            rules_list = []

        # If rules list has basic rules, we can fetch explanations for critical ones
        enriched_rules: List[Dict[str, Any]] = []
        for r in rules_list:
            if isinstance(r, dict):
                enriched_rules.append(r)

        state["rules"] = enriched_rules
        logger.info(f"[rules_node] Loaded {len(enriched_rules)} business rules")

    except Exception as exc:
        logger.warning(f"[rules_node] Rules retrieval warning: {exc}")
        state["rules"] = []

    return state
