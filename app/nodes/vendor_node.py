import logging
from typing import Any, Dict, List
from app.clients.vendor_client import VendorClient
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def vendor_node(state: SimulationState) -> SimulationState:
    """
    LangGraph Node: Vendor & Supplier Intelligence
    Loads vendor information, supplier risk scores, and supplier hierarchy.
    """
    logger.info("[vendor_node] Loading vendor intelligence")
    state["current_node"] = "vendor"
    client = VendorClient()

    try:
        vendor_response = await client.get_vendors(limit=100)
        vendors_list = vendor_response.get("vendors", [])

        # If empty or not list, ensure list structure
        if not isinstance(vendors_list, list):
            vendors_list = []

        # Optionally enrich top vendors with detailed risk scores
        enriched_vendors: List[Dict[str, Any]] = []
        for v in vendors_list[:20]:
            vendor_id = v.get("vendor_id")
            if vendor_id and "component_scores" not in v:
                try:
                    detail = await client.get_vendor_detail(vendor_id)
                    enriched_vendors.append(detail)
                    continue
                except Exception:
                    pass
            enriched_vendors.append(v)

        state["vendors"] = enriched_vendors if enriched_vendors else vendors_list
        logger.info(f"[vendor_node] Loaded {len(state['vendors'])} vendors")

    except Exception as exc:
        logger.warning(f"[vendor_node] Vendor retrieval warning: {exc}")
        state["vendors"] = []

    return state
