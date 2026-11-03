import logging
from typing import Any, Dict
from app.clients.market_risk_client import MarketRiskClient
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def market_risk_node(state: SimulationState) -> SimulationState:
    """
    LangGraph Node: Market Risk & FX Exposure
    Loads foreign exchange exposure, currency risk indicators, and volatility cases.
    """
    logger.info("[market_risk_node] Loading market risk and FX exposure")
    state["current_node"] = "market_risk"
    client = MarketRiskClient()

    try:
        fx_exposure = {}
        try:
            fx_exposure = await client.get_fx_exposure(limit=50)
        except Exception as exc:
            logger.debug(f"[market_risk_node] Could not fetch fx_exposure: {exc}")

        currency_score = {}
        try:
            currency_score = await client.get_currency_risk_score()
        except Exception as exc:
            logger.debug(f"[market_risk_node] Could not fetch currency_score: {exc}")

        risk_dist = {}
        try:
            risk_dist = await client.get_risk_distribution()
        except Exception as exc:
            logger.debug(f"[market_risk_node] Could not fetch risk_distribution: {exc}")

        state["market_risk_data"] = {
            "fx_exposure": fx_exposure,
            "currency_risk_score": currency_score,
            "risk_distribution": risk_dist,
        }
        logger.info("[market_risk_node] Market risk telemetry successfully consolidated")

    except Exception as exc:
        logger.warning(f"[market_risk_node] Market risk retrieval warning: {exc}")
        state["market_risk_data"] = {
            "fx_exposure": {},
            "currency_risk_score": {},
            "risk_distribution": {},
        }

    return state
