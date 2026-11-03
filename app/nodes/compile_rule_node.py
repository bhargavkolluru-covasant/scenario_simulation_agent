import logging
from typing import Optional
from app.services.rule_compilation_service import RuleCompilationService
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def compile_rule_node(
    state: SimulationState,
    service: Optional[RuleCompilationService] = None,
) -> SimulationState:
    """
    LangGraph Node: Rule Compilation
    Integrates with ARIIA Compile Rule API to translate scenario context
    into compiled executable business rules. Populates state['compiled_rules'].
    """
    logger.info("[compile_rule_node] Compiling scenario into business risk rules")
    state["current_node"] = "compile_rule"

    compilation_service = service or RuleCompilationService()

    # Input: state.scenario with fallback to state.query
    scenario_input = state.get("scenario") or state.get("query", "")

    try:
        response = await compilation_service.compile_rule(scenario_input)

        # Output: state.compiled_rules
        state["compiled_rules"] = response
        state["compiled_rule"] = response  # Backward compatibility
        state["compile_status"] = response.get("success", True)

        rule_details = response.get("rule", {})
        rule_name = rule_details.get("name", "Generated Rule") if isinstance(rule_details, dict) else "Rule"
        logger.info(f"[compile_rule_node] Successfully registered compiled rule: '{rule_name}'")

    except Exception as exc:
        logger.error(f"[compile_rule_node] Error compiling rule: {exc}", exc_info=True)
        state["compiled_rules"] = {
            "success": False,
            "error": str(exc),
            "rule": None,
        }
        state["compile_status"] = False

    return state


class CompileRuleNode:
    """Class wrapper for backward compatibility."""

    def __init__(self, service: Optional[RuleCompilationService] = None):
        self.service = service or RuleCompilationService()

    async def execute(self, state: SimulationState) -> SimulationState:
        return await compile_rule_node(state, service=self.service)