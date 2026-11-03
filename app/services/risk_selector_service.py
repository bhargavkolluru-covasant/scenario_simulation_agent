import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return " ".join(
            part for part in (_text(item) for item in value.values()) if part
        )
    if isinstance(value, list):
        return " ".join(part for part in (_text(item) for item in value) if part)
    return ""


class RiskSelectorService:
    """Create evidence-grounded fallback risks when semantic reasoning has none."""

    def select_risks(self, state: Dict[str, Any]) -> Dict[str, Any]:
        dashboard_semantics = state.get("dashboard_semantics") or {}
        scenario_semantics = state.get("scenario_semantics") or {}
        primary_kpi = state.get("primary_kpi") or {}
        supporting_kpis = state.get("supporting_kpis") or []
        if not isinstance(primary_kpi, dict):
            primary_kpi = {}
        if not isinstance(supporting_kpis, list):
            supporting_kpis = []

        primary_name = str(primary_kpi.get("name") or "selected dashboard indicator")
        scenario_context = _text(scenario_semantics) or str(state.get("query") or "")
        dashboard_context = _text(dashboard_semantics)

        primary_risk = {
            "name": f"{primary_name} Impact Risk",
            "severity": "MEDIUM",
            "business_impact": (
                f"The scenario may change {primary_name}; assess the resulting effect "
                "against the business context represented by the dashboard."
            ),
            "reason": "Derived from the selected KPI and the supplied dashboard and scenario context.",
            "scenario_context": scenario_context,
            "dashboard_context": dashboard_context,
            "source": "semantic_context_fallback",
        }

        secondary_risk: Optional[Dict[str, Any]] = None
        secondary_kpi = next(
            (
                item
                for item in supporting_kpis
                if isinstance(item, dict) and item.get("name")
            ),
            None,
        )
        if secondary_kpi:
            secondary_name = str(secondary_kpi["name"])
            secondary_risk = {
                "name": f"{secondary_name} Exposure Risk",
                "severity": "LOW",
                "business_impact": (
                    f"Movement in {secondary_name} may amplify or offset the primary "
                    "scenario impact and should be monitored alongside it."
                ),
                "reason": "Derived from a supporting KPI selected for this dashboard scenario.",
                "scenario_context": scenario_context,
                "dashboard_context": dashboard_context,
                "source": "semantic_context_fallback",
            }

        result = {
            "primary_risk": primary_risk,
            "secondary_risk": secondary_risk,
        }
        logger.info(
            "[RiskSelectorService] Created context-based fallback risk for KPI=%s",
            primary_name,
        )
        return result
