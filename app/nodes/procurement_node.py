import logging
from typing import Any, Dict
from app.clients.procurement_client import ProcurementClient
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def procurement_node(state: SimulationState) -> SimulationState:
    """
    LangGraph Node: Procurement & Supply Chain Intelligence
    Loads purchase orders, procurement stats, and trends for supply chain impact analysis.
    """
    logger.info("[procurement_node] Loading procurement and PO data")
    state["current_node"] = "procurement"
    client = ProcurementClient()

    try:
        po_response = await client.get_purchase_orders(limit=50)
        purchase_orders = po_response.get("purchase_orders", [])
        total_count = po_response.get("total_count", len(purchase_orders))

        stats = {}
        try:
            stats = await client.get_procurement_stats()
        except Exception as exc:
            logger.debug(f"[procurement_node] Could not fetch stats: {exc}")

        state["procurement_data"] = {
            "purchase_orders": purchase_orders,
            "total_count": total_count,
            "stats": stats,
        }
        logger.info(f"[procurement_node] Loaded {len(purchase_orders)} purchase orders")

    except Exception as exc:
        logger.warning(f"[procurement_node] Procurement retrieval warning: {exc}")
        state["procurement_data"] = {
            "purchase_orders": [],
            "total_count": 0,
            "stats": {},
        }

    return state
