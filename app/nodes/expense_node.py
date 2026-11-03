import logging
from typing import Any, Dict
from app.clients.expense_client import ExpenseClient
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def expense_node(state: SimulationState) -> SimulationState:
    """
    LangGraph Node: Expense & Operational Cost Intelligence
    Loads operational expenses and spend anomalies for cost impact modeling.
    """
    logger.info("[expense_node] Loading expense data")
    state["current_node"] = "expense"
    client = ExpenseClient()

    try:
        exp_response = await client.get_expenses(page=1, page_size=20)
        expenses = exp_response.get("expenses", [])
        total_count = exp_response.get("total_count", len(expenses))

        stats = {}
        try:
            stats = await client.get_expense_stats()
        except Exception as exc:
            logger.debug(f"[expense_node] Could not fetch stats: {exc}")

        state["expense_data"] = {
            "expenses": expenses,
            "total_count": total_count,
            "stats": stats,
        }
        logger.info(f"[expense_node] Loaded {len(expenses)} expenses")

    except Exception as exc:
        logger.warning(f"[expense_node] Expense retrieval warning: {exc}")
        state["expense_data"] = {
            "expenses": [],
            "total_count": 0,
            "stats": {},
        }

    return state
