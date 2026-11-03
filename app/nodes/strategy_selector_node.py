import json
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from app.services.llm_gateway import LLMGateway
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


class SimulationStrategy(str, Enum):
    """
    Simulation execution strategies supported by the ARIIA agent.
    Domain-aware strategies mapped to executive scenario types.
    """
    PORTFOLIO_OPTIMIZATION = "PORTFOLIO_OPTIMIZATION"
    PROJECT_DELIVERY_SIMULATION = "PROJECT_DELIVERY_SIMULATION"
    CUSTOMER_EXPERIENCE_SIMULATION = "CUSTOMER_EXPERIENCE_SIMULATION"
    SUPPLY_CHAIN = "SUPPLY_CHAIN"
    FINANCIAL_IMPACT = "FINANCIAL_IMPACT"
    MARKET_RISK = "MARKET_RISK"
    RULE_BASED = "RULE_BASED"
    HYBRID = "HYBRID"


class StrategyDecision(BaseModel):
    strategy: SimulationStrategy
    rationale: Optional[str] = Field(default="", description="Reasoning for selecting this simulation strategy")


def determine_strategy(
    scenario: Dict[str, Any],
    dashboard_category: str = "",
    scenario_category: str = "",
    is_capital_allocation: bool = False,
    query: str = "",
) -> SimulationStrategy:
    """
    Deterministic domain-aware strategy selection based on dashboard context and scenario intent.
    Node 6: Simulation Strategy Selector.
    """
    combined_text = " ".join([
        query,
        str(scenario.get("description") or ""),
        str(scenario.get("change_type") or ""),
        str(scenario.get("scenario_type") or ""),
        str(scenario.get("domain") or ""),
    ]).casefold()

    dashboard_category = str(dashboard_category or "").upper()
    scenario_category = str(scenario_category or "").upper()

    # 1. Capital Allocation & Portfolio Prioritization
    if (
        is_capital_allocation
        or scenario_category in {"CAPITAL_ALLOCATION", "PORTFOLIO_OPTIMIZATION", "INVESTMENT_VIABILITY"}
        or dashboard_category in {"LAND_FEASIBILITY", "PORTFOLIO"}
        or any(k in combined_text for k in ("capital", "priorit", "hbu", "hurdle", "irr", "allocation"))
    ):
        return SimulationStrategy.PORTFOLIO_OPTIMIZATION

    # 2. Project Delay & Critical Path Delivery
    if (
        dashboard_category == "PROJECT_DELIVERY"
        or scenario_category == "PROJECT_DELIVERY"
        or any(k in combined_text for k in ("delay", "handover", "schedule", "milestone", "critical path", "slippage"))
    ):
        return SimulationStrategy.PROJECT_DELIVERY_SIMULATION

    # 3. Customer Experience & Retention
    if (
        dashboard_category == "CUSTOMER"
        or scenario_category == "CUSTOMER_SATISFACTION"
        or any(k in combined_text for k in ("csat", "nps", "churn", "retention", "customer satisfaction"))
    ):
        return SimulationStrategy.CUSTOMER_EXPERIENCE_SIMULATION

    # 4. Supply Chain / Vendor Failure
    if (
        dashboard_category == "PROCUREMENT"
        or any(k in combined_text for k in ("vendor", "supplier", "sourcing", "purchase order"))
    ):
        return SimulationStrategy.SUPPLY_CHAIN

    # 5. Financial & Liquidity
    if (
        dashboard_category in {"FINANCE", "SALES"}
        or any(k in combined_text for k in ("cash flow", "liquidity", "margin", "invoice", "revenue"))
    ):
        return SimulationStrategy.FINANCIAL_IMPACT

    # 6. Compliance & Governance
    if (
        dashboard_category == "COMPLIANCE"
        or any(k in combined_text for k in ("audit", "compliance", "regulatory", "violation"))
    ):
        return SimulationStrategy.RULE_BASED

    return SimulationStrategy.HYBRID


async def strategy_selector_node(
    state: SimulationState,
    llm_service: Optional[LLMGateway] = None,
) -> SimulationState:
    """
    Node 6: Simulation Strategy Selector
    Assigns domain-aware simulation execution strategy based on:
    Dashboard Context + Scenario Intent. Populates state['strategy'] and state['simulation_strategy_context'].
    """
    logger.info("[strategy_selector_node] Selecting simulation execution strategy")
    state["current_node"] = "strategy_selector"

    try:
        scenario = state.get("scenario", {})
        query = str(state.get("query") or "")
        dashboard_category = str(
            (state.get("dashboard_context") or {}).get("category")
            or state.get("dashboard_category")
            or ""
        )
        scenario_context = state.get("scenario_context") or {}
        scenario_category = str(scenario_context.get("scenario_category") or "")
        is_capital_allocation = bool(scenario_context.get("is_capital_allocation", False))

        strategy = determine_strategy(
            scenario=scenario,
            dashboard_category=dashboard_category,
            scenario_category=scenario_category,
            is_capital_allocation=is_capital_allocation,
            query=query,
        )

        methodology_map = {
            SimulationStrategy.PORTFOLIO_OPTIMIZATION: [
                "Ranking", "Optimization", "Portfolio Prioritization", "Hurdle Rate Compliance",
            ],
            SimulationStrategy.PROJECT_DELIVERY_SIMULATION: [
                "Critical Path Impact", "Schedule Risk", "Delivery Simulation", "Contractor Dependency",
            ],
            SimulationStrategy.CUSTOMER_EXPERIENCE_SIMULATION: [
                "Customer Retention", "Revenue Pressure", "Customer Risk", "Churn Sensitivity",
            ],
            SimulationStrategy.FINANCIAL_IMPACT: [
                "Cash Flow Timing", "Working Capital Drag", "Margin Stress",
            ],
            SimulationStrategy.SUPPLY_CHAIN: [
                "Supplier Dependency", "Material Lead Time", "Procurement Alternate Sourcing",
            ],
            SimulationStrategy.RULE_BASED: [
                "Regulatory Policy Validation", "Control Enforcement",
            ],
            SimulationStrategy.HYBRID: [
                "Cross-Domain Multi-Variable Simulation",
            ],
        }

        state["simulation_strategy"] = strategy.value
        state["simulation_strategy_context"] = {
            "strategy": strategy.value,
            "methodology": methodology_map.get(strategy, ["Standard Simulation"]),
            "dashboard_category": dashboard_category,
            "scenario_category": scenario_category,
        }

        logger.info(
            f"[strategy_selector_node] Strategy assigned: '{strategy.value}' "
            f"(Methodology: {state['simulation_strategy_context']['methodology']})"
        )
    except Exception as exc:
        logger.error(f"[strategy_selector_node] Error evaluating strategy: {exc}", exc_info=True)
        state["simulation_strategy"] = SimulationStrategy.PORTFOLIO_OPTIMIZATION.value

    return state


class StrategySelectorNode:
    """Class wrapper for backward compatibility."""

    def __init__(self, llm_service: Optional[LLMGateway] = None):
        self.llm_service = llm_service

    async def execute(self, state: SimulationState) -> SimulationState:
        return await strategy_selector_node(state, llm_service=self.llm_service)
