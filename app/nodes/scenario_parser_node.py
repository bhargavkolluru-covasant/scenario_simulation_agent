import logging
from typing import Optional
from app.services.scenario_parser_service import ScenarioParserService
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def scenario_parser_node(
    state: SimulationState,
    service: Optional[ScenarioParserService] = None,
) -> SimulationState:
    """
    LangGraph Node: Scenario Parser
    Transforms natural language query in state['query'] into a structured, validated simulation
    scenario stored in state['scenario'].
    """
    logger.info("[scenario_parser_node] Parsing user query into structured scenario")
    state["current_node"] = "scenario_parser"

    parser = service or ScenarioParserService()
    query = state.get("query", "")

    try:
        scenario = await parser.parse(query)
        state["scenario"] = scenario
        logger.info(
            f"[scenario_parser_node] Successfully generated scenario: {scenario.get('scenario_type')} "
            f"for entity '{scenario.get('target_entity')}'"
        )
    except Exception as exc:
        logger.error(f"[scenario_parser_node] Failed to parse scenario: {exc}", exc_info=True)
        # Fallback safe minimal scenario
        state["scenario"] = {
            "scenario_type": "enterprise_scenario",
            "target_entity": "Unknown Entity",
            "change_type": "scenario_change",
            "change_percentage": 0.0,
            "time_horizon": "unspecified",
            "domain": "unspecified",
            "description": f"Fallback scenario derived from query: {query}",
        }

    return state


class ScenarioParserNode:
    """Class wrapper for backward compatibility with object-oriented node invocations."""

    def __init__(self, service: Optional[ScenarioParserService] = None):
        self.service = service or ScenarioParserService()

    async def execute(self, state: SimulationState) -> SimulationState:
        return await scenario_parser_node(state, service=self.service)