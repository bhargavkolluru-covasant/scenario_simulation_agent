import logging
from typing import Optional
from app.services.financial_reasoning_service import FinancialReasoningService
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def financial_reasoning_selector_node(
    state: SimulationState,
    service: Optional[FinancialReasoningService] = None,
) -> SimulationState:
    """
    Node 7: Financial Reasoning Selector
    Selects domain-aware financial impact logic based on Scenario Intent and Dashboard Context.
    Populates state['financial_reasoning'].
    """
    logger.info("[financial_reasoning_selector_node] Selecting domain financial reasoning model")
    state["current_node"] = "financial_reasoning_selector"

    reasoning_service = service or FinancialReasoningService()
    reasoning = reasoning_service.select_financial_reasoning(state)

    state["financial_reasoning"] = reasoning

    logger.info(
        "[financial_reasoning_selector_node] Selected financial model: %s",
        reasoning.get("model_type"),
    )
    return state


class FinancialReasoningSelectorNode:
    """Class wrapper for backward compatibility."""

    def __init__(self, service: Optional[FinancialReasoningService] = None):
        self.service = service or FinancialReasoningService()

    async def execute(self, state: SimulationState) -> SimulationState:
        return await financial_reasoning_selector_node(state, service=self.service)
