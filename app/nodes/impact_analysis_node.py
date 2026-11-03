import logging
from app.services.impact_analysis_service import ImpactAnalysisService
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def impact_analysis_node(state: SimulationState) -> SimulationState:
    """
    LangGraph Node: Multidimensional Impact Analysis
    Evaluates operational disruption, financial exposure, regulatory compliance, and blast radius.
    """
    logger.info("[impact_analysis_node] Running impact analysis")
    state["current_node"] = "impact_analysis"
    service = ImpactAnalysisService()

    try:
        impact_result = await service.analyze(state)
        state["impact_result"] = impact_result
        logger.info(f"[impact_analysis_node] Impact analyzed: {impact_result.get('overall_severity')} ({impact_result.get('overall_impact_score')}/100)")
    except Exception as exc:
        logger.error(f"[impact_analysis_node] Impact analysis error: {exc}")
        state["impact_result"] = {
            "overall_impact_score": 0.0,
            "overall_severity": "UNKNOWN",
            "error": str(exc),
            "dimensions": [],
        }

    return state
