import logging
import uuid
from typing import Any, Dict, Iterable, List, Optional

from app.services.financial_model_service import FinancialModelService

logger = logging.getLogger(__name__)

_RECORD_LIST_KEYS = {"kpis", "insights", "items", "results", "metrics"}
_VALUE_KEYS = (
    "value",
    "current_value",
    "metric_value",
    "amount",
    "score",
    "percentage",
)


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("%", "")
        try:
            return float(cleaned)
        except ValueError:
            return None
    if isinstance(value, dict):
        for key in _VALUE_KEYS:
            number = _number(value.get(key))
            if number is not None:
                return number
    return None


def _records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    for key, value in payload.items():
        if key.lower() in _RECORD_LIST_KEYS and isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    for value in payload.values():
        nested = _records(value)
        if nested:
            return nested

    return []


def _record_label(record: Dict[str, Any]) -> str:
    return " ".join(
        str(record.get(key, ""))
        for key in (
            "name",
            "title",
            "label",
            "metric",
            "metric_name",
            "kpi",
            "kpi_name",
            "description",
            "key",
        )
    ).lower()


def _named_number(
    records: Iterable[Dict[str, Any]], terms: Iterable[str]
) -> Optional[float]:
    for record in records:
        label = _record_label(record)
        if any(term in label for term in terms):
            for key in _VALUE_KEYS:
                number = _number(record.get(key))
                if number is not None:
                    return number
    return None


def _record_number(record: Dict[str, Any]) -> Optional[float]:
    for key in _VALUE_KEYS:
        number = _number(record.get(key))
        if number is not None:
            return number
    return None


def _field_number(payload: Dict[str, Any], terms: Iterable[str]) -> float:
    for key, value in payload.items():
        if any(term in key.lower() for term in terms):
            number = _number(value)
            if number is not None:
                return number
        if isinstance(value, dict):
            number = _field_number(value, terms)
            if number:
                return number
    return 0.0


class SimulationService:
    """Simulate enterprise scenarios from ARIIA dashboards, KPIs, actions, rules, and graph data."""

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state.get("query", "")
        scenario = state.get("scenario", {})
        dashboard_rows = state.get("dashboard_rows", [])
        if not isinstance(dashboard_rows, list):
            dashboard_rows = []
        matched_records = state.get("matched_dashboard_records", [])
        if not isinstance(matched_records, list):
            matched_records = []
        entity_match_summary = state.get("entity_match_summary", {})
        if not isinstance(entity_match_summary, dict):
            entity_match_summary = {}
        kpi_insights = state.get("kpi_insights", {})
        actions = state.get("actions", [])
        action_stats = state.get("action_stats", {})
        rules = state.get("rules", [])
        knowledge_graph_data = state.get("knowledge_graph_data", {})
        graph_nodes = knowledge_graph_data.get("nodes", [])
        if not isinstance(graph_nodes, list):
            graph_nodes = []
        graph_summary = state.get("graph_summary") or knowledge_graph_data.get(
            "graph_summary", {}
        )
        related_entities = state.get("related_entities") or knowledge_graph_data.get(
            "related_entities", []
        )
        dependency_paths = state.get("dependency_paths") or knowledge_graph_data.get(
            "dependency_paths", []
        )
        blast_radius = state.get("blast_radius") or knowledge_graph_data.get(
            "blast_radius", {}
        )
        root_cause_candidates = state.get("root_cause_candidates") or knowledge_graph_data.get(
            "root_cause_candidates", []
        )
        if not isinstance(related_entities, list):
            related_entities = []
        if not isinstance(dependency_paths, list):
            dependency_paths = []
        if not isinstance(blast_radius, dict):
            blast_radius = {}
        if not isinstance(root_cause_candidates, list):
            root_cause_candidates = []
        if not isinstance(graph_summary, dict):
            graph_summary = {}

        kpi_records = _records(kpi_insights)
        target_entity = entity_match_summary.get("target_entity", "")

        dashboard_data = state.get("dashboard_data")
        if not dashboard_data:
            dashboard_data = {"matched_dashboard_records": matched_records}
        financial_model = FinancialModelService().model(
            scenario={**scenario, "query": query} if isinstance(scenario, dict) else query,
            dashboard_data=dashboard_data,
            kpi_insights=kpi_insights,
            actions=actions,
            rules=rules,
        )
        existing_totals = financial_model["current_exposure"]["total_by_currency"]
        scenario_totals = financial_model["scenario_exposure"][
            "estimated_amount_by_currency"
        ]
        baseline_exposure = (
            next(iter(existing_totals.values()))
            if len(existing_totals) == 1
            else 0.0
        )
        scenario_exposure = (
            next(iter(scenario_totals.values()))
            if len(scenario_totals) == 1
            else 0.0
        )
        simulated_exposure = round(scenario_exposure, 2)
        variance_pct = round(
            scenario_exposure / baseline_exposure * 100.0,
            2,
        ) if baseline_exposure else 0.0

        change_pct = _number(scenario.get("change_percentage")) or 0.0

        risk_score = _named_number(
            kpi_records, ("risk", "exposure", "incident", "compliance")
        )
        if risk_score is None:
            risk_score = 35.0
        if 0 <= risk_score <= 1:
            risk_score *= 100.0

        risk_score = min(max(risk_score, 0), 100)
        impact_probability = min(
            round((risk_score / 100.0) * (0.5 + min(change_pct, 100.0) / 200.0), 3),
            0.95,
        )

        action_count = len(actions) if isinstance(actions, list) else 0
        critical_action_count = int(
            _field_number(action_stats, ("critical_action", "critical_count"))
        )
        overdue_action_count = int(
            _field_number(action_stats, ("overdue_action", "overdue_count"))
        )
        compliance_count = sum(
            1
            for record in kpi_records
            if any(term in _record_label(record) for term in ("compliance finding", "compliance issue", "violation"))
            and (_record_number(record) or 0) > 0
        )
        compliance_count += sum(
            1
            for rule in rules
            if isinstance(rule, dict) and str(rule.get("severity", "")).upper() == "CRITICAL"
        )

        summary_text = (
            f"Scenario simulation completed for '{query}'. "
            f"Dashboard Records Evaluated: {len(dashboard_rows)}; "
            f"Matched Records: {len(matched_records)}; "
            f"Entity Match Count: "
            f"{entity_match_summary.get('entity_match_count', len(matched_records))}. "
            f"{len(kpi_records)} KPI insights, {action_count} recommended actions, "
            f"{len(rules)} business rules, and "
            f"{len(graph_nodes)} knowledge-graph nodes. "
            f"Graph propagation identified {len(related_entities)} related entities "
            f"across {len(dependency_paths)} dependency paths. "
            "Current enterprise exposure and scenario-attributable financial estimates "
            "are reported separately."
        )

        return {
            "scenario_id": f"SCEN-{uuid.uuid4().hex[:8].upper()}",
            "scenario_name": f"ARIIA Enterprise Simulation: {query[:60]}",
            "target_entities": [target_entity] if target_entity else [],
            "parameters": {
                "impact_probability": impact_probability,
                "risk_score": round(risk_score, 2),
                "scenario_change_percentage": change_pct,
                "dashboard_records_count": len(dashboard_rows),
                "matched_records_count": len(matched_records),
                "kpi_count": len(kpi_records),
                "actions_count": action_count,
                "critical_actions_count": critical_action_count,
                "overdue_actions_count": overdue_action_count,
                "rules_count": len(rules),
                "knowledge_graph_nodes": len(graph_nodes),
                "knowledge_graph_related_entities": len(related_entities),
                "knowledge_graph_dependency_paths": len(dependency_paths),
                "knowledge_graph_usable": bool(
                    graph_summary.get("usable_for_simulation", False)
                ),
                "compliance_findings_count": compliance_count,
            },
            "metrics": {
                "baseline_financial_exposure": round(baseline_exposure, 2),
                "simulated_financial_exposure": simulated_exposure,
                "exposure_variance_percentage": variance_pct,
                "scenario_incremental_financial_exposure": round(scenario_exposure, 2),
                "financial_model": financial_model,
                "impact_probability": impact_probability,
                "risk_score": round(risk_score, 2),
                "compliance_findings_count": compliance_count,
                "critical_actions_count": critical_action_count,
                "overdue_actions_count": overdue_action_count,
            },
            "kpi_metrics": kpi_records,
            "dashboard_records": matched_records[:100],
            "recommended_actions": actions[:100] if isinstance(actions, list) else [],
            "business_rules": rules[:100],
            "knowledge_graph_entities": graph_nodes[:100],
            "knowledge_graph_stats": knowledge_graph_data.get("stats", {}),
            "graph_summary": graph_summary,
            "related_entities": related_entities[:100],
            "dependency_paths": dependency_paths[:100],
            "blast_radius": blast_radius,
            "blast_radius_entities": blast_radius.get("affected_entities", [])[:100],
            "root_cause_candidates": root_cause_candidates[:20],
            "knowledge_graph_context": {
                "graph_summary": graph_summary,
                "related_entities": related_entities[:100],
                "dependency_paths": dependency_paths[:100],
                "blast_radius": blast_radius,
                "root_cause_candidates": root_cause_candidates[:20],
            },
            "dashboard_context": {
                "matched_dashboard_records": matched_records,
                "entity_match_summary": entity_match_summary,
            },
            "summary": summary_text,
            "financial_model": financial_model,
        }
