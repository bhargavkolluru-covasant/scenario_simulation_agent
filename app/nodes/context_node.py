import logging
from typing import Dict, Any

from app.config.settings import settings
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


class ContextInitializationError(Exception):
    """Raised when execution context cannot be initialized."""
    pass


async def context_node(
    state: SimulationState
) -> SimulationState:
    """
    LangGraph Node: Context Initialization

    Purpose:
    - Initialize execution context
    - Resolve the active enterprise and domain
    - Populate state context
    - Provide a consistent execution environment
      for downstream nodes

    NOTE:
    Enterprise and Domain are already selected
    by the ARIIA platform before the user enters
    the agent.

    Scope is retained as optional backward-compatible context.
    """

    logger.info(
        "[context_node] Initializing execution context"
    )

    state["current_node"] = "context"

    try:

        enterprise_id = state.get("enterprise_id") or settings.enterprise_id
        domain_ids = state.get("domain_ids") or settings.domain_ids
        scope_id = state.get("scope_id") or settings.scope_id or ""

        if not enterprise_id or not domain_ids:
            raise ContextInitializationError(
                "ARIIA enterprise_id and domain_ids are required."
            )

        context: Dict[str, Any] = {
            "enterprise_id": enterprise_id,
            "domain_ids": domain_ids,
            "scope_id": scope_id,
        }

        state["enterprise_id"] = enterprise_id
        state["domain_ids"] = domain_ids
        state["scope_id"] = scope_id
        state["context"] = context

        logger.info(
            "[context_node] Context initialized for enterprise=%s domains=%s",
            enterprise_id,
            domain_ids,
        )

    except Exception as exc:

        logger.error(
            "[context_node] Context initialization "
            f"failed: {exc}"
        )

        state["error"] = str(exc)
        state["status"] = "FAILED"

        raise

    return state