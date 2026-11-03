import logging
import asyncio

from app.clients.actions_client import ActionsClient
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def actions_node(state: SimulationState) -> SimulationState:
    """Load platform-recommended business actions and their aggregate metrics."""
    logger.info("[actions_node] Loading recommended actions")
    state["current_node"] = "actions"
    client = ActionsClient(
        auth_token=state.get("access_token"),
        enterprise_id=state.get("enterprise_id"),
        domain_ids=state.get("domain_ids"),
        scope_id=state.get("scope_id"),
    )
    actions, action_stats = await asyncio.gather(
        client.get_actions(),
        client.get_action_stats(),
    )
    state["available_actions"] = actions
    state["action_stats"] = action_stats
    logger.info("[actions_node] Loaded %d recommended actions", len(actions))
    return state
