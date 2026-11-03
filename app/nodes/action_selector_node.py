import logging
from typing import Optional

from app.services.action_selector_service import (
    ActionSelectorService,
)

from app.state.simulation_state import (
    SimulationState,
)

logger = logging.getLogger(__name__)


async def action_selector_node(
    state: SimulationState,
    service: Optional[
        ActionSelectorService
    ] = None,
) -> SimulationState:

    logger.info(
        "[action_selector_node] Generating actions"
    )

    state["current_node"] = (
        "action_selector"
    )

    semantic = state.get(
        "semantic_reasoning",
        {},
    )

    if not isinstance(semantic, dict):
        semantic = {}
    semantic_actions = semantic.get("actions") or []
    if not isinstance(semantic_actions, list):
        semantic_actions = []
    if not semantic_actions:
        existing_actions = state.get("selected_actions")
        if isinstance(existing_actions, list):
            semantic_actions = existing_actions

    # --------------------------------------------------
    # LLM DRIVEN ACTIONS
    # --------------------------------------------------

    if semantic_actions:

        logger.info("[action_selector_node] Using selected semantic actions")

        state["selected_actions"] = (
            semantic_actions
        )

        state["actions"] = (
            semantic_actions
        )

        logger.info(
            "[action_selector_node] Selected %d semantic actions",
            len(semantic_actions),
        )

        return state

    # --------------------------------------------------
    # LEGACY FALLBACK
    # --------------------------------------------------

    action_service = (
        service
        or ActionSelectorService()
    )

    actions = (
        action_service.select_actions(
            state
        )
    )

    state["selected_actions"] = (
        actions
    )

    state["actions"] = actions

    logger.info(
        "[action_selector_node] Selected %d fallback actions",
        len(actions),
    )

    return state


class ActionSelectorNode:
    """
    Class wrapper for backward compatibility.
    """

    def __init__(
        self,
        service: Optional[
            ActionSelectorService
        ] = None,
    ):
        self.service = (
            service
            or ActionSelectorService()
        )

    async def execute(
        self,
        state: SimulationState,
    ) -> SimulationState:

        return await action_selector_node(
            state,
            service=self.service,
        )