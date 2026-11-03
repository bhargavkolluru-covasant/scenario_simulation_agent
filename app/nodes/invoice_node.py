import logging
from typing import Any, Dict
from app.clients.invoice_client import InvoiceClient
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def invoice_node(state: SimulationState) -> SimulationState:
    """
    LangGraph Node: Invoice & Financial Liability
    Loads invoices, overdue liabilities, and payment records for financial impact modeling.
    """
    logger.info("[invoice_node] Loading invoice data")
    state["current_node"] = "invoice"
    client = InvoiceClient()

    try:
        inv_response = await client.get_invoices(limit=50)
        invoices = inv_response.get("invoices", [])
        total_count = inv_response.get("total_count", len(invoices))

        stats = {}
        try:
            stats = await client.get_invoice_stats()
        except Exception as exc:
            logger.debug(f"[invoice_node] Could not fetch stats: {exc}")

        state["invoice_data"] = {
            "invoices": invoices,
            "total_count": total_count,
            "stats": stats,
        }
        logger.info(f"[invoice_node] Loaded {len(invoices)} invoices")

    except Exception as exc:
        logger.warning(f"[invoice_node] Invoice retrieval warning: {exc}")
        state["invoice_data"] = {
            "invoices": [],
            "total_count": 0,
            "stats": {},
        }

    return state
