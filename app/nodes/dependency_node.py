"""
OBSOLETE / DEPRECATED:
dependency_node is obsolete and no longer used in the enterprise simulation agent architecture.
Do NOT use or register this node in the workflow.
"""
import warnings
from app.state.simulation_state import SimulationState


async def dependency_node(state: SimulationState) -> SimulationState:
    """
    Deprecated dependency node. Not part of the simulation agent workflow.
    """
    warnings.warn(
        "dependency_node is obsolete and deprecated. Do not use in workflow.",
        DeprecationWarning,
        stacklevel=2,
    )
    return state