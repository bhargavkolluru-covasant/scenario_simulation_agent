import logging
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def recommendation_node(state: SimulationState) -> SimulationState:
    """
    LangGraph Node: Next Best Action & Recommendation Synthesis
    Synthesizes concrete, prioritized mitigation recommendations based on simulation and impact analysis.
    """
    logger.info("[recommendation_node] Generating risk mitigation recommendations")
    state["current_node"] = "recommendation"
    selected_actions = state.get("selected_actions") or []
    if not isinstance(selected_actions, list):
        selected_actions = []
    state["recommendations"] = list(selected_actions)
    logger.info(
        "[recommendation_node] Forwarded %d selected actions",
        len(selected_actions),
    )

    return state
