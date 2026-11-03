import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FinancialReasoningService:
    """
    Node 7: Financial Reasoning Selector
    Selects domain-aware financial impact logic based on Scenario Intent and Dashboard Context:
    - Capital Reduction: Investment Prioritization, IRR, Cost of Capital, Portfolio Ranking
    - Project Delay: Revenue Recognition Delay, Collections Delay, Cashflow Impact
    - Customer Satisfaction: Retention Impact, Revenue Impact
    """

    def select_financial_reasoning(self, state: Dict[str, Any]) -> Dict[str, Any]:
        dashboard_context = state.get("dashboard_context") or {}
        dashboard_category = str(
            dashboard_context.get("category") or state.get("dashboard_category") or ""
        ).upper()

        scenario_context = state.get("scenario_context") or {}
        scenario_category = str(scenario_context.get("scenario_category") or "").upper()
        is_capital_allocation = scenario_context.get("is_capital_allocation", False)

        query = str(state.get("query") or "")
        scenario = state.get("scenario") or {}
        scenario_text = " ".join([
            query,
            str(scenario.get("description") or ""),
            str(scenario.get("change_type") or ""),
        ]).casefold()

        change_pct = scenario.get("change_percentage")
        if change_pct is None:
            pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", scenario_text)
            change_pct = float(pct_match.group(1)) if pct_match else 30.0
        else:
            try:
                change_pct = float(change_pct)
            except (ValueError, TypeError):
                change_pct = 30.0

        entity = (
            state.get("primary_business_entity")
            or (state.get("scenario") or {}).get("target_entity")
            or "the evaluated portfolio"
        )

        # 1. Capital Reduction / Portfolio Allocation Logic
        if dashboard_category in {"LAND_FEASIBILITY", "PORTFOLIO"} or is_capital_allocation or scenario_category == "CAPITAL_ALLOCATION":
            return self._build_capital_allocation_reasoning(entity, change_pct, state)

        # 2. Project Delay Logic
        if dashboard_category == "PROJECT_DELIVERY" or scenario_category == "PROJECT_DELIVERY" or any(k in scenario_text for k in ("delay", "handover", "slippage", "schedule")):
            return self._build_project_delay_reasoning(entity, scenario_text, state)

        # 3. Customer Satisfaction / Churn Logic
        if dashboard_category == "CUSTOMER" or scenario_category == "CUSTOMER_SATISFACTION" or any(k in scenario_text for k in ("csat", "nps", "churn", "retention")):
            return self._build_customer_reasoning(entity, change_pct, state)

        # 4. Default Financial Impact Logic
        return self._build_default_financial_reasoning(entity, state)

    def _build_capital_allocation_reasoning(
        self,
        entity: str,
        change_pct: float,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "model_type": "CAPITAL_ALLOCATION_OPTIMIZATION",
            "primary_drivers": [
                "Investment Prioritization",
                "Internal Rate of Return (IRR)",
                "Cost of Capital & Hurdle Rate",
                "Portfolio Ranking (Weighted Score)",
                "Gross Development Value (GDV) vs Development Cost",
            ],
            "formula": (
                f"Constrained Capital Ceiling = Baseline Allocation × (1 - {change_pct:.0f}%); "
                "Feasibility Criterion = Option IRR ≥ Hurdle Rate (12%) & Weighted Score Ranking"
            ),
            "derivation": (
                f"Under a {change_pct:.0f}% capital reduction for {entity}, available investment capital "
                "must be rationed strictly according to risk-adjusted return and feasibility hurdle rates. "
                "Development candidates with highest weighted score and IRR above hurdle rate (e.g. OPT-0003 at 18% IRR vs 12% hurdle) "
                "are prioritized for full capital commitment. Intermediate candidates (e.g. OPT-0021 at 15% IRR) receive secondary allocation, "
                "while lowest-ranking or hurdle-breaching options (e.g. OPT-0009) are deferred to protect portfolio capital liquidity."
            ),
            "executive_summary": (
                f"A {change_pct:.0f}% reduction in investment capital requires disciplined portfolio ranking. "
                "Prioritizing high-scoring options above the hurdle rate preserves risk-adjusted GDV yield and prevents capital misallocation."
            ),
            "assumptions": [
                "Capital envelope applies as a strict ceiling across active development candidates.",
                "Development options exceeding hurdle rate (12%) maintain investment committee funding priority.",
                "Deferred candidates preserve zoning and planning rights without incurring premature capital expenditure.",
            ],
            "investment_impact": (
                f"Capital allocation shifts to concentrate scarce equity on Tier-1 development options for {entity}, "
                f"releasing an estimated {change_pct:.0f}% capital buffer and optimizing portfolio hurdle compliance."
            ),
        }

    def _build_project_delay_reasoning(
        self,
        entity: str,
        scenario_text: str,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        days_match = re.search(r"(\d+)\s*(?:days?|months?)", scenario_text)
        delay_duration = days_match.group(0) if days_match else "90 days"
        return {
            "model_type": "MILESTONE_REVENUE_RECOGNITION_DELAY",
            "primary_drivers": [
                "Revenue Recognition Delay",
                "Milestone Collections Delay",
                "Cashflow Timing Drag",
                "Contractor Acceleration Cost vs Liquidated Damages",
            ],
            "formula": "Working Capital Drag = Daily Milestones at Risk × Delay Days; Asset GDV = Constant",
            "derivation": (
                f"A {delay_duration} handover delay on {entity} defers final completion certificate milestones, "
                "postponing buyer handover collections and statutory revenue recognition without reducing nominal contract value. "
                "Working capital is impacted through delayed collection inflows and potential contractor prolongation costs."
            ),
            "executive_summary": (
                f"{entity} handover delay shifts revenue recognition and milestone cash inflows by {delay_duration}, "
                "increasing working capital financing drag while underlying commercial asset value remains intact."
            ),
            "assumptions": [
                "Sales contracts remain in force with no material buyer rescission.",
                "Deferred collections shift into subsequent fiscal quarters without bad-debt write-downs.",
                "Delay penalties are bounded by contractual liquidated damages caps.",
            ],
            "investment_impact": (
                f"Preserves total contract value while shifting cash collection timing on {entity}; "
                "recommends critical path recovery to mitigate working capital interest carry."
            ),
        }

    def _build_customer_reasoning(
        self,
        entity: str,
        change_pct: float,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "model_type": "CUSTOMER_RETENTION_REVENUE_PRESSURE",
            "primary_drivers": [
                "Customer Retention Impact",
                "Net Revenue at Churn Risk",
                "Customer Lifetime Value (LTV) Pressure",
                "Customer Acquisition & Recovery Cost",
            ],
            "formula": f"Revenue at Risk = Baseline Contract Value × Estimated Churn Sensitivity ({change_pct:.0f}%)",
            "derivation": (
                f"Degradation in customer satisfaction metrics for {entity} increases account renewal attrition risk. "
                "Every percentage point of customer churn directly compresses annual recurring revenue (ARR) and escalates recovery costs."
            ),
            "executive_summary": (
                f"Customer experience and retention pressure on {entity} threatens commercial recurring revenue streams, "
                "warranting immediate executive key account retention intervention."
            ),
            "assumptions": [
                "Customer churn exhibits proportional sensitivity to CSAT and NPS degradation.",
                "Proactive executive outreach recovers a substantial portion of at-risk accounts.",
            ],
            "investment_impact": (
                f"Directs retention investment to high-LTV customer accounts for {entity} to protect recurring cash flows."
            ),
        }

    def _build_default_financial_reasoning(
        self,
        entity: str,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "model_type": "OPERATIONAL_FINANCIAL_EXPOSURE",
            "primary_drivers": [
                "Operating Cash Flow Buffer",
                "Direct Disruption Expense",
                "Contingency Reserve Allocation",
            ],
            "formula": "Financial Exposure = Direct Operational Cost Variance + Working Capital Impact",
            "derivation": (
                f"Financial exposure on {entity} is modeled from operational cost variances and working capital timing buffers."
            ),
            "executive_summary": (
                f"Operational stress on {entity} introduces potential budget variance and requires contingency monitoring."
            ),
            "assumptions": ["Contingency reserves are available to absorb immediate variance."],
            "investment_impact": "Maintains disciplined expenditure controls across affected operational cost centers.",
        }
