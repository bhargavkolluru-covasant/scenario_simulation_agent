import logging
from typing import Optional
from app.services.explainability_service import ExplainabilityService
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def explainability_node(
    state: SimulationState,
    service: Optional[ExplainabilityService] = None,
) -> SimulationState:
    """
    LangGraph Node: Explainability Engine
    Synthesizes executive-friendly explanations of simulation outcomes, key risk drivers,
    multidimensional business impacts, and recommendation rationale. Populates state['explanation'].
    """
    logger.info("[explainability_node] Generating executive-level outcome explanation")
    state["current_node"] = "explainability"

    explain_service = service or ExplainabilityService()

    try:
        explanation = await explain_service.explain(scenario_or_state=state)

        state["explanation"] = explanation
        logger.info("[explainability_node] Executive explanation successfully generated")

    except Exception as exc:
        logger.error(f"[explainability_node] Error during explanation generation: {exc}", exc_info=True)
        state["explanation"] = {
            "executive_summary": (
                "A complete executive narrative could not be generated. "
                "Review the scenario with the relevant business owners."
            ),
            "current_business_context": (
                "Current context should be confirmed against the matched business records."
            ),
            "business_impact": (
                "The scenario may affect business outcomes; confirm dependencies before acting."
            ),
            "financial_impact": (
                "No reliable financial narrative could be generated from the available assessment."
            ),
            "operational_impact": (
                "Review operational dependencies and service commitments relevant to the scenario."
            ),
            "key_risks": [
                "The business impact remains uncertain until the scenario is reviewed."
            ],
            "recommended_response": (
                "Validate the assessment with accountable business owners and agree proportionate mitigations."
            ),
            "executive_conclusion": (
                "Defer material decisions until the scenario evidence has been reviewed."
            ),
            "key_drivers": [
                "The business impact remains uncertain until the scenario is reviewed."
            ],
            "risk_explanation": (
                "The business impact remains uncertain until the scenario is reviewed."
            ),
            "recommendation_rationale": (
                "Validate the assessment with accountable business owners."
            ),
        }

    return state


class ExplainabilityNode:
    """Class wrapper for backward compatibility."""

    def __init__(self, service: Optional[ExplainabilityService] = None):
        self.service = service or ExplainabilityService()

    async def execute(self, state: SimulationState) -> SimulationState:
        return await explainability_node(state, service=self.service)
