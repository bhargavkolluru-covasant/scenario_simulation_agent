import logging
from app.services.simulation_service import SimulationService
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def simulation_node(state: SimulationState) -> SimulationState:
    """
    LangGraph Node: Simulation Engine Execution
    Passes unified upstream context to the Simulation Engine to model operational and financial scenarios.
    """
    logger.info("[simulation_node] Running scenario simulation")
    state["current_node"] = "simulation"
    service = SimulationService()

    try:
        simulation_result = await service.run(state)
        state["simulation_result"] = simulation_result
        logger.info("[simulation_node] Simulation completed successfully")
    except Exception as exc:
        logger.error(f"[simulation_node] Simulation execution error: {exc}")
        state["simulation_result"] = {
            "scenario_id": "ERR-SIM",
            "scenario_name": "Failed Simulation",
            "error": str(exc),
            "metrics": {},
        }

    return state
