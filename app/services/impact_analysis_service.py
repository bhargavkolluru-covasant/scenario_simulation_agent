import logging
from typing import Any, Dict, List, Tuple

from app.services.financial_model_service import FinancialModelService
from app.services.causal_reasoning_service import CausalReasoningService

logger = logging.getLogger(__name__)

_KPI_NAME_KEYS = ("kpi_name", "name", "title", "label", "metric")
_KPI_VALUE_KEYS = (
    "kpi_value",
    "value",
    "current_value",
    "metric_value",
    "score",
    "amount",
)
def _kpi_records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("kpis", "recent_kpis", "insights", "items", "data", "results"):
        records = payload.get(key)
        if isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]
    raw = payload.get("raw")
    if isinstance(raw, dict):
        summary = raw.get("kpi_summary")
        if isinstance(summary, dict) and isinstance(summary.get("recent_kpis"), list):
            return [item for item in summary["recent_kpis"] if isinstance(item, dict)]
    return []


def _kpi_text(record: Dict[str, Any], keys: Tuple[str, ...]) -> str:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _amount_label(amount: float, currency: str) -> str:
    formatted = f"{amount:,.2f}".rstrip("0").rstrip(".")
    return f"{currency} {formatted}" if currency else formatted


def _severity_for_score(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "moderate"
    return "low"


class ImpactAnalysisService:
    """
    Service for Multidimensional Impact Analysis.
    Evaluates scenario impact, financial exposure, governance, and other enterprise risk
    based on simulation results and upstream domain telemetry.
    """

    async def analyze(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate comprehensive impact across scenario, financial, and governance dimensions.
        """
        simulation_result = state.get("simulation_result", {})
        rules = state.get("rules", [])
        matched_records = state.get("matched_dashboard_records", [])
        kpi_insights = state.get("kpi_insights", {})
        actions = state.get("actions", [])
        action_stats = state.get("action_stats", {})
        knowledge_graph_data = state.get("knowledge_graph_data", {})
        if not isinstance(knowledge_graph_data, dict):
            knowledge_graph_data = {}
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
        if not isinstance(graph_summary, dict):
            graph_summary = {}
        if not isinstance(related_entities, list):
            related_entities = []
        if not isinstance(dependency_paths, list):
            dependency_paths = []
        if not isinstance(blast_radius, dict):
            blast_radius = {}

        logger.info("[ImpactAnalysisService] Analyzing scenario impact")

        metrics = simulation_result.get("metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}
        disruption_prob = metrics.get("impact_probability", 0.0)
        risk_score = float(metrics.get("risk_score", 0.0) or 0.0)
        critical_actions = int(metrics.get("critical_actions_count", 0) or 0)
        overdue_actions = int(metrics.get("overdue_actions_count", 0) or 0)
        compliance_findings = int(metrics.get("compliance_findings_count", 0) or 0)
        action_risk_score = min(
            critical_actions * 10.0 + overdue_actions * 5.0,
            100.0,
        )
        operational_kpi = next(
            (
                record for record in _kpi_records(kpi_insights)
                if any(term in _kpi_text(record, _KPI_NAME_KEYS).casefold() for term in (
                    "risk", "delay", "delivery", "variance", "overrun", "compliance",
                ))
            ),
            None,
        )
        financial_model = simulation_result.get("financial_model") or metrics.get(
            "financial_model"
        )
        if not isinstance(financial_model, dict):
            financial_model = FinancialModelService().model(
                scenario={**state.get("scenario", {}), "query": state.get("query", "")}
                if isinstance(state.get("scenario", {}), dict)
                else state.get("query", ""),
                dashboard_data=state.get("dashboard_data", {}),
                kpi_insights=kpi_insights,
                actions=actions,
                rules=rules,
            )
        existing_model = financial_model.get(
            "current_exposure",
            financial_model.get("existing_enterprise_exposure", {}),
        )
        scenario_model = financial_model.get(
            "scenario_exposure",
            financial_model.get("scenario_incremental_exposure", {}),
        )
        combined_model = financial_model.get(
            "combined_outlook",
            financial_model.get("combined_risk_outlook", {}),
        )
        existing_items = existing_model.get("items", []) if isinstance(existing_model, dict) else []
        financial_evidence = [
            {
                "category": "Current Enterprise Exposure",
                "name": item.get("name", "Enterprise exposure"),
                "value": item.get("formatted_amount", ""),
                "currency": item.get("currency", ""),
            }
            for item in existing_items
            if isinstance(item, dict)
        ]
        scenario_amounts = (
            scenario_model.get("estimated_amount_by_currency", {})
            if isinstance(scenario_model, dict)
            else {}
        )
        if not isinstance(scenario_amounts, dict):
            scenario_amounts = {}
        if len(scenario_amounts) == 1:
            financial_currency, scenario_amount = next(iter(scenario_amounts.items()))
            try:
                fin_at_risk = max(float(scenario_amount or 0), 0.0)
            except (TypeError, ValueError):
                fin_at_risk = 0.0
        else:
            financial_currency = ""
            fin_at_risk = 0.0
        financial_exposure_source = "simulation" if fin_at_risk else "unquantified"
        financial_exposure_label = (
            _amount_label(fin_at_risk, financial_currency) if fin_at_risk else ""
        )
        financial_exposure_direction = (
            "increases" if fin_at_risk else "unquantified"
        )
        compliance_action_count = self._find_metric(
            action_stats, ("compliance_action", "compliance_finding")
        )
        # 1. Dimension: Scenario Impact
        op_score = min(
            round(
                max(
                    disruption_prob * 100.0,
                    risk_score,
                    action_risk_score,
                ),
                1,
            ),
            100.0,
        )
        op_severity = "CRITICAL" if op_score >= 75 else ("HIGH" if op_score >= 50 else ("MEDIUM" if op_score >= 25 else "LOW"))
        if operational_kpi:
            indicator = _kpi_text(operational_kpi, _KPI_NAME_KEYS)
            indicator_value = _kpi_text(operational_kpi, _KPI_VALUE_KEYS)
            indicator_unit = _kpi_text(operational_kpi, ("kpi_unit", "unit", "uom"))
            if indicator_unit and indicator_unit.casefold() not in indicator_value.casefold():
                indicator_value = f"{indicator_value} {indicator_unit}".strip()
            operational_description = (
                f"A {_severity_for_score(op_score)} operational risk exists due to "
                f"{indicator.casefold()}"
                + (f" ({indicator_value})" if indicator_value else "")
                + "."
            )
        else:
            operational_description = (
                f"A {_severity_for_score(op_score)} operational risk may affect "
                "business performance under the scenario."
            )
        op_dimension = {
            "dimension_name": "Scenario Impact",
            "severity": op_severity,
            "score": op_score,
            "impact_description": operational_description,
            "evidence": [],
        }

        # 2. Dimension: Financial & Liquidity Exposure
        combined_financial_risk = str(
            combined_model.get(
                "severity",
                scenario_model.get("severity", "UNQUANTIFIED")
                if isinstance(scenario_model, dict)
                else "UNQUANTIFIED",
            )
            if isinstance(combined_model, dict)
            else "UNQUANTIFIED"
        ).upper()
        if combined_financial_risk == "UNQUANTIFIED":
            combined_financial_risk = "LOW"
        fin_score = {
            "CRITICAL": 85.0,
            "HIGH": 65.0,
            "MEDIUM": 40.0,
            "LOW": 15.0,
        }.get(combined_financial_risk, 15.0)
        fin_severity = "CRITICAL" if fin_score >= 75 else ("HIGH" if fin_score >= 50 else ("MEDIUM" if fin_score >= 25 else "LOW"))
        current_names = [
            str(item.get("name"))
            for item in existing_items[:3]
            if isinstance(item, dict) and item.get("name")
        ]
        if fin_at_risk:
            fin_description = (
                f"The scenario model estimates incremental exposure of "
                f"{financial_exposure_label}; current enterprise exposures are reported separately."
            )
        elif isinstance(scenario_model, dict) and scenario_model.get("severity") not in (
            None,
            "UNQUANTIFIED",
        ):
            fin_description = (
                f"The scenario presents {str(scenario_model.get('severity')).lower()} "
                "qualitative risk across the affected business indicators; a monetary increment is not quantified."
            )
        elif current_names:
            fin_description = (
                "Current enterprise exposure indicators include "
                + ", ".join(current_names)
                + "; no scenario-attributable monetary impact can be quantified from available inputs."
            )
        else:
            fin_description = (
                "No scenario-attributable monetary impact can be quantified from the available inputs."
            )
        fin_evidence = [
            f"Scenario incremental estimate: {financial_exposure_label}"
        ] if fin_at_risk else []
        fin_evidence.extend(
            f"Current enterprise exposure: {item['name']} {item.get('value', '')}".strip()
            for item in financial_evidence[:5]
        )
        fin_dimension = {
            "dimension_name": "Financial & Liquidity Exposure",
            "severity": fin_severity,
            "score": fin_score,
            "impact_description": fin_description,
            "evidence": fin_evidence,
        }

        # 3. Dimension: Compliance & Governance Rule Violations
        # Check rules against scenario data
        triggered_rules = []
        for r in rules:
            rule_id = r.get("rule_id", "")
            rule_name = r.get("name", "Enterprise Rule")
            severity = r.get("severity", "MEDIUM")

            # Check if conditions correlate with scenario flags
            is_triggered = False
            if r.get("triggered") or severity == "CRITICAL":
                is_triggered = True

            if is_triggered:
                triggered_rules.append({
                    "rule_id": rule_id,
                    "name": rule_name,
                    "severity": severity,
                    "category": r.get("category", "General"),
                    "target_entity": r.get("target_entity", "General"),
                })

        violations_count = max(
            len(triggered_rules),
            compliance_findings,
            int(compliance_action_count),
        )
        comp_score = min(violations_count * 20.0, 100.0)
        comp_severity = "CRITICAL" if comp_score >= 75 else ("HIGH" if comp_score >= 50 else ("MEDIUM" if comp_score >= 25 else "LOW"))
        comp_dimension = {
            "dimension_name": "Regulatory & Internal Rule Compliance",
            "severity": comp_severity,
            "score": comp_score,
            "impact_description": (
                "Compliance or governance requirements may be affected under the scenario."
                if violations_count
                else "No material compliance or governance concern was identified in the available evidence."
            ),
            "evidence": [f"Rule '{r['name']}' ({r['severity']})" for r in triggered_rules[:5]],
        }

        # 4. Dimension: Additional Scenario Risk
        additional_risk_score = risk_score
        mkt_severity = "HIGH" if additional_risk_score >= 50 else ("MEDIUM" if additional_risk_score >= 25 else "LOW")
        mkt_dimension = {
            "dimension_name": "Additional Scenario Risk",
            "severity": mkt_severity,
            "score": round(additional_risk_score, 1),
            "impact_description": (
                f"A {_severity_for_score(additional_risk_score)} additional business risk remains "
                "under the simulated conditions."
            ),
            "evidence": [],
        }

        # Overall synthesis
        graph_is_usable = bool(
            graph_summary.get("usable_for_simulation")
            and graph_summary.get("graph_exists")
            and graph_summary.get("total_nodes", 0) > 0
            and graph_summary.get("total_edges", 0) > 0
            and related_entities
        )
        try:
            blast_radius_score = float(
                blast_radius.get("blast_radius_score", 0.0) or 0.0
            )
        except (TypeError, ValueError):
            blast_radius_score = 0.0
        blast_radius_score = min(max(blast_radius_score, 0.0), 100.0)
        relationships = [
            str(relationship).casefold()
            for path in dependency_paths
            if isinstance(path, dict)
            for relationship in (
                path.get("relationships", [])
                if isinstance(path.get("relationships", []), list)
                else []
            )
        ]
        risk_relationship_terms = (
            "depend", "contract", "invoice", "payment", "deliver", "delay",
            "risk", "impact", "obligation", "supply",
        )
        relationship_risk_score = (
            round(
                sum(
                    1 for relationship in relationships
                    if any(term in relationship for term in risk_relationship_terms)
                ) / max(len(relationships), 1) * 100.0,
                1,
            )
            if graph_is_usable and relationships
            else 0.0
        )
        graph_influence_score = (
            round(blast_radius_score * 0.6 + relationship_risk_score * 0.4, 1)
            if graph_is_usable
            else 0.0
        )
        graph_dimension = {
            "dimension_name": "Knowledge Graph Dependency Impact",
            "severity": (
                "CRITICAL" if graph_influence_score >= 75 else
                "HIGH" if graph_influence_score >= 50 else
                "MEDIUM" if graph_influence_score >= 25 else "LOW"
            ),
            "score": graph_influence_score,
            "impact_description": (
                f"Graph relationships identify {len(related_entities)} affected entities "
                f"across {len(dependency_paths)} dependency paths."
            ),
            "evidence": [
                f"Blast radius score: {blast_radius_score:.1f}/100",
                f"Relationship risk score: {relationship_risk_score:.1f}/100",
            ],
        }
        dimensions = [op_dimension, fin_dimension, comp_dimension, mkt_dimension]
        if graph_is_usable:
            dimensions.append(graph_dimension)
        overall_score = round(sum(d["score"] for d in dimensions) / len(dimensions), 1)
        overall_severity = "CRITICAL" if overall_score >= 70 else ("HIGH" if overall_score >= 50 else ("MEDIUM" if overall_score >= 25 else "LOW"))

        affected_entities = []
        for item in related_entities:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("entity_name") or item.get("node_id")
            if name:
                affected_entities.append({
                    "name": str(name),
                    "node_type": item.get("node_type"),
                    "depth": item.get("depth"),
                    "relationship_type": item.get("relationship_type"),
                })
        blast_radius_entities = list(dict.fromkeys(
            list(simulation_result.get("target_entities", []))
            + [item["name"] for item in affected_entities]
        ))

        narrative = (
            f"The scenario presents a {overall_severity.casefold()} overall business impact. "
            f"Primary exposure is {op_dimension['impact_description']} "
            f"{fin_description}"
        )
        if graph_is_usable:
            narrative += " Business relationships indicate possible downstream effects."

        impact_result = {
            "overall_impact_score": overall_score,
            "overall_severity": overall_severity,
            "dimensions": dimensions,
            "violations_count": violations_count,
            "triggered_rules": triggered_rules,
            "financial_exposure_at_risk": fin_at_risk,
            "financial_exposure_source": financial_exposure_source,
            "financial_exposure_currency": financial_currency,
            "financial_exposure_label": financial_exposure_label,
            "financial_exposure_direction": financial_exposure_direction,
            "financial_exposure_evidence": financial_evidence,
            "financial_model": financial_model,
            "financial_reasoning": (
                scenario_model.get("financial_reasoning", "")
                if isinstance(scenario_model, dict)
                else ""
            ),
            "financial_impact_drivers": (
                scenario_model.get("impact_drivers", [])
                if isinstance(scenario_model, dict)
                else []
            ),
            "financial_confidence": financial_model.get("confidence", 0.0),
            "blast_radius_entities": blast_radius_entities,
            "affected_entities": affected_entities,
            "dependency_impact": {
                "path_count": len(dependency_paths),
                "paths": dependency_paths[:50],
            },
            "blast_radius_score": blast_radius_score,
            "relationship_risk_score": relationship_risk_score,
            "graph_influence_score": graph_influence_score,
            "root_cause_candidates": (
                state.get("root_cause_candidates", [])
                if isinstance(state.get("root_cause_candidates", []), list)
                else []
            ),
            "analysis_narrative": narrative,
            "action_stats": action_stats,
        }
        scenario = state.get("scenario", {})
        if isinstance(scenario, dict):
            scenario = {
                **scenario,
                "query": state.get("query") or scenario.get("query", ""),
            }
        elif state.get("query"):
            scenario = f"{scenario} {state['query']}".strip()
        causal_analysis = CausalReasoningService().analyze(
            scenario=scenario,
            dashboard_data=state.get("dashboard_data", {}),
            matched_dashboard_records=matched_records,
            kpi_insights=kpi_insights,
            actions=actions,
            rules=rules,
            impact_result=impact_result,
            graph_summary=graph_summary,
            dependency_paths=dependency_paths,
            related_entities=related_entities,
            matched_entities=state.get("entity_match_summary"),
            primary_kpi=state.get("primary_kpi"),
            supporting_kpis=state.get("supporting_kpis", []),
        )
        impact_result["causal_analysis"] = causal_analysis
        impact_result["root_cause_analysis"] = causal_analysis["root_cause_analysis"]
        if isinstance(scenario_model, dict):
            scenario_model["causal_chain"] = causal_analysis["causal_chain"]
            scenario_model["primary_impact_path"] = causal_analysis["primary_impact_path"]
            scenario_model["causal_confidence"] = causal_analysis["confidence"]
            scenario_model["causal_kpi"] = causal_analysis["primary_kpi"]

        return impact_result

    @classmethod
    def _find_metric(cls, payload: Any, terms: Tuple[str, ...]) -> float:
        if isinstance(payload, dict):
            for key, value in payload.items():
                if any(term in key.lower() for term in terms):
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        pass
                nested = cls._find_metric(value, terms)
                if nested:
                    return nested
        elif isinstance(payload, list):
            for item in payload:
                nested = cls._find_metric(item, terms)
                if nested:
                    return nested
        return 0.0
