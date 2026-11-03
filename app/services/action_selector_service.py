import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _context_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return " ".join(
            item for item in (_context_text(child) for child in value.values()) if item
        )
    if isinstance(value, list):
        return " ".join(item for item in (_context_text(child) for child in value) if item)
    return ""


class ActionSelectorService:
    """Create targeted fallback actions from the already selected risks and KPI."""

    def select_actions(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        primary_kpi = state.get("primary_kpi") or {}
        if not isinstance(primary_kpi, dict):
            primary_kpi = {}
        kpi_name = str(primary_kpi.get("name") or "selected dashboard indicator")

        risks = [
            risk
            for risk in (
                state.get("primary_risk"),
                state.get("secondary_risk"),
            )
            if isinstance(risk, dict) and risk.get("name")
        ]
        if not risks:
            logger.warning(
                "[ActionSelectorService] No selected risks; cannot derive fallback actions"
            )
            return []

        dashboard_context = _context_text(state.get("dashboard_semantics"))
        scenario_context = (
            _context_text(state.get("scenario_semantics"))
            or str(state.get("query") or "")
        )
        entity = str(
            state.get("primary_business_entity")
            or (state.get("scenario") or {}).get("target_entity")
            or "the affected business area"
        )

        actions = [
            {
                "horizon": "Immediate",
                "title": f"Assess {kpi_name} for {entity}",
                "action": (
                    f"Validate the current {kpi_name} baseline and quantify its "
                    f"exposure to the stated scenario: {scenario_context}"
                ),
                "priority": "HIGH",
                "business_benefit": (
                    f"Establishes an evidence-based view of {kpi_name} and "
                    f"{risks[0]['name']} in the context of {dashboard_context or entity}."
                ),
                "expected_outcome": (
                    f"A documented baseline and impact estimate for {kpi_name}."
                ),
                "source": "selected_risk_kpi_fallback",
            },
        ]
        actions.extend(
            {
                "horizon": "Near term",
                "title": f"Set monitoring thresholds for {risk['name']}",
                "action": (
                    f"Define a measurable trigger for {risk['name']} using "
                    f"{kpi_name}, assign an accountable owner, and review it against "
                    "the scenario assumptions."
                ),
                "priority": "MEDIUM",
                "business_benefit": str(
                    risk.get("business_impact")
                    or f"Provides timely visibility into {risk['name']}."
                ),
                "expected_outcome": (
                    f"An owner, trigger, and review cadence for {risk['name']}."
                ),
                "source": "selected_risk_kpi_fallback",
            }
            for risk in risks
        )
        return actions[:3]
