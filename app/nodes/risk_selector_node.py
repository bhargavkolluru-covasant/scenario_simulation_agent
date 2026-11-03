import logging
from typing import Optional

from app.services.risk_selector_service import RiskSelectorService
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def risk_selector_node(
    state: SimulationState,
    service: Optional[RiskSelectorService] = None,
) -> SimulationState:
    """
    Node 4: Risk Selector

    Uses semantic reasoning output if available.

    Falls back to legacy RiskSelectorService
    if semantic output is unavailable.
    """

    logger.info(
        "[risk_selector_node] Selecting dashboard-aware and scenario-aware risks"
    )

    state["current_node"] = "risk_selector"

    semantic = state.get("semantic_reasoning", {})
    if not isinstance(semantic, dict):
        semantic = {}

    # ---------------------------------
    # NEW LLM-DRIVEN PATH
    # ---------------------------------
    if isinstance(semantic.get("primary_risk"), dict):

        logger.info(
            "[risk_selector_node] Using semantic risk output"
        )

        state["primary_risk"] = semantic["primary_risk"]
        semantic_secondary = semantic.get("secondary_risk")
        state["secondary_risk"] = (
            semantic_secondary if isinstance(semantic_secondary, dict) else None
        )

        state["risk_context"] = {
            "primary_risk": state["primary_risk"],
            "secondary_risk": state["secondary_risk"],
            "source": "semantic_reasoning",
        }

    elif not isinstance(state.get("primary_risk"), dict):

        # ---------------------------------
        # FALLBACK LEGACY RULE ENGINE
        # ---------------------------------
        risk_service = (
            service
            or RiskSelectorService()
        )

        result = risk_service.select_risks(
            state
        )

        state["primary_risk"] = (
            result["primary_risk"]
        )

        state["secondary_risk"] = (
            result.get("secondary_risk")
        )

        state["risk_context"] = result
    else:
        state["risk_context"] = {
            "primary_risk": state["primary_risk"],
            "secondary_risk": state.get("secondary_risk"),
            "source": "state",
        }

    logger.info(
        "[risk_selector_node] Primary Risk='%s' Secondary Risk='%s'",
        (state.get("primary_risk") or {}).get("name"),
        (
            (state.get("secondary_risk") or {}).get("name")
            if state.get("secondary_risk")
            else "None"
        ),
    )

    return state


class RiskSelectorNode:
    """
    Class wrapper for backward compatibility.
    """

    def __init__(
        self,
        service: Optional[
            RiskSelectorService
        ] = None,
    ):
        self.service = (
            service
            or RiskSelectorService()
        )

    async def execute(
        self,
        state: SimulationState,
    ) -> SimulationState:
        return await risk_selector_node(
            state,
            service=self.service,
        )