import re
from typing import Any, Dict, List, Optional, Tuple

from app.services.financial_model_service import classify_kpi
from app.services.root_cause_analysis_service import RootCauseAnalysisService


_KPI_NAME_KEYS = ("kpi_name", "metric_name", "name", "title", "label", "metric")
_KPI_VALUE_KEYS = ("kpi_value", "value", "current_value", "metric_value", "score", "amount", "count")
_CONFIDENCE_KEYS = ("confidence_score", "confidence")
_KPI_COLLECTIONS = ("kpis", "recent_kpis", "insights", "items", "data", "results")
_SCENARIO_CATEGORY_TERMS = {
    "CUSTOMER_EXPERIENCE": (
        "customer experience", "customer satisfaction", "satisfaction", "customer",
        "client experience", "retention", "complaint", "loyalty", "csat",
    ),
    "FINANCIAL": (
        "financial", "finance", "cash flow", "cashflow", "liquidity", "revenue", "profit",
        "margin", "cost", "funding", "receivable", "payable", "sales",
        "pricing", "collection", "collections", "budget",
    ),
    "OPERATIONAL": (
        "operational", "throughput", "capacity", "productivity", "efficiency",
        "downtime", "delivery", "quality", "inventory", "shortage", "output",
        "production", "manufacturing", "construction", "procurement", "supplier",
        "schedule", "lead time", "project execution", "handover", "delay", "delayed",
        "late", "slippage",
    ),
    "COMPLIANCE": (
        "compliance", "regulatory", "violation", "audit", "policy", "penalty",
        "control breach",
    ),
    "STRATEGIC": (
        "strategic", "strategy", "growth", "market share", "objective",
        "investment", "transformation", "portfolio", "value realization",
    ),
    "RISK": (
        "risk", "exposure", "incident", "threat", "continuity", "resilience",
        "vulnerability",
    ),
}
_STOP_WORDS = {
    "about", "after", "again", "against", "could", "does", "during", "from",
    "have", "into", "might", "more", "most", "should", "than", "that", "their",
    "there", "these", "this", "through", "under", "what", "when", "where",
    "which", "while", "with", "would", "will", "into", "risk", "scenario",
    "change", "increases", "increase", "decreases", "decrease", "declines",
    "decline", "drops", "drop", "falls", "fall", "rises", "rise",
}
_GRAPH_SUMMARY_KEYS = ("name", "entity_name", "node_id", "relationship_type")


def _records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in _KPI_COLLECTIONS:
        records = payload.get(key)
        if isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]
    raw = payload.get("raw")
    summary = raw.get("kpi_summary") if isinstance(raw, dict) else None
    recent = summary.get("recent_kpis") if isinstance(summary, dict) else None
    return [item for item in recent if isinstance(item, dict)] if isinstance(recent, list) else []


def _scenario_text(scenario: Any) -> str:
    if isinstance(scenario, dict):
        return " ".join(
            str(scenario[key])
            for key in (
                "query",
                "description",
                "change_type",
                "change_description",
                "scenario_type",
                "scenario_category",
                "category",
                "domain",
                "target_entity",
                "direction",
            )
            if scenario.get(key) not in (None, "")
        )
    return str(scenario or "")


def classify_scenario(scenario: Any, kpi_records: Optional[List[Dict[str, Any]]] = None) -> str:
    """Classify scenario intent before considering unrelated current KPI exposure."""
    if isinstance(scenario, dict):
        explicit_category = str(
            scenario.get("scenario_category")
            or scenario.get("category")
            or scenario.get("risk_category")
            or ""
        ).strip().upper().replace("-", "_").replace(" ", "_")
        aliases = {
            "CUSTOMER": "CUSTOMER_EXPERIENCE",
            "CUSTOMER_EXPERIENCE": "CUSTOMER_EXPERIENCE",
            "FINANCE": "FINANCIAL",
            "FINANCIAL": "FINANCIAL",
            "OPERATIONS": "OPERATIONAL",
            "OPERATIONAL": "OPERATIONAL",
            "COMPLIANCE": "COMPLIANCE",
            "RISK": "RISK",
            "STRATEGY": "STRATEGIC",
            "STRATEGIC": "STRATEGIC",
        }
        if explicit_category in aliases:
            return aliases[explicit_category]
    text = _scenario_text(scenario).casefold()
    category_scores = {
        category: sum(
            1 for term in terms
            if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text)
        )
        for category, terms in _SCENARIO_CATEGORY_TERMS.items()
    }
    if any(category_scores.values()):
        priority = ("CUSTOMER_EXPERIENCE", "COMPLIANCE", "FINANCIAL", "OPERATIONAL", "STRATEGIC", "RISK")
        return max(priority, key=lambda category: (category_scores[category], -priority.index(category)))
    if kpi_records:
        primary = max(
            kpi_records,
            key=lambda record: _kpi_relevance(record, _tokens(text), [])[:2],
        )
        return {
            "CUSTOMER": "CUSTOMER_EXPERIENCE",
        }.get(classify_kpi(primary), classify_kpi(primary))
    return "RISK"


def _text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {_text(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return " ".join(_text(item) for item in value)
    return "" if value is None else str(value)


def _brief(value: Any, words: int = 18) -> str:
    parts = " ".join(_text(value).split()).split()
    return " ".join(parts[:words]) + ("…" if len(parts) > words else "")


def _confidence(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if 1 < number <= 100:
        number /= 100
    return min(max(number, 0.0), 1.0)


def _tokens(value: str) -> set[str]:
    return {
        token.casefold()
        for token in re.findall(r"[a-zA-Z0-9]+", value)
        if len(token) > 2 and token.casefold() not in _STOP_WORDS
    }


def _kpi_name(record: Dict[str, Any]) -> str:
    return str(next(
        (record[key] for key in _KPI_NAME_KEYS if record.get(key) not in (None, "")),
        "Business indicator",
    ))


def _kpi_reasoning(record: Dict[str, Any]) -> str:
    return _text(
        record.get("reasoning")
        or record.get("explanation")
        or record.get("rationale")
        or record.get("description")
    )


def _kpi_value(record: Dict[str, Any]) -> Any:
    return next(
        (record[key] for key in _KPI_VALUE_KEYS if record.get(key) not in (None, "")),
        None,
    )


def _kpi_relevance(
    record: Dict[str, Any],
    scenario_terms: set[str],
    matched_records: List[Dict[str, Any]],
    scenario_category: Optional[str] = None,
    matched_entities: Any = None,
) -> Tuple[float, float, float, float, float]:
    label = _kpi_name(record)
    reasoning = _kpi_reasoning(record)
    kpi_terms = _tokens(f"{label} {reasoning}")
    overlap = len(scenario_terms.intersection(kpi_terms))
    category_aliases = {
        "CUSTOMER_EXPERIENCE": "CUSTOMER",
    }
    category = str(scenario_category or "").upper()
    category_match = float(
        bool(category)
        and classify_kpi(record)
        == category_aliases.get(category, category)
    )
    entity_values = []
    if isinstance(record.get("entities"), list):
        entity_values.extend(_text(record["entities"]).split())
    for key in (
        "entity",
        "entity_name",
        "customer",
        "account",
        "vendor",
        "project",
        "site",
        "plant",
        "department",
        "business_unit",
    ):
        if record.get(key) not in (None, ""):
            entity_values.append(_text(record[key]))
    entity_terms = _tokens(" ".join(entity_values))
    matched_entity_values = []
    if isinstance(matched_entities, dict):
        for key in ("target_entity", "matched_entities", "entities"):
            value = matched_entities.get(key)
            if value not in (None, ""):
                matched_entity_values.append(_text(value))
    elif isinstance(matched_entities, (list, tuple, set)):
        matched_entity_values.extend(_text(item) for item in matched_entities)
    elif matched_entities not in (None, ""):
        matched_entity_values.append(_text(matched_entities))
    for matched_record in matched_records[:250]:
        if not isinstance(matched_record, dict):
            continue
        for key in (
            "entity",
            "entity_name",
            "customer",
            "account",
            "vendor",
            "project",
            "site",
            "plant",
            "department",
            "business_unit",
        ):
            if matched_record.get(key) not in (None, ""):
                matched_entity_values.append(_text(matched_record[key]))
    matched_entity_terms = _tokens(" ".join(matched_entity_values))
    entity_match = float(
        bool(entity_terms.intersection(matched_entity_terms))
        or bool(kpi_terms.intersection(matched_entity_terms))
    )
    dashboard_terms = _tokens(" ".join(
        _text(item) for item in matched_records[:250]
    ))
    dashboard_support = float(bool(kpi_terms.intersection(dashboard_terms)))
    overlap_score = min(overlap / 2, 1.0)
    relevance = (
        category_match * 0.35
        + overlap_score * 0.35
        + entity_match * 0.2
        + dashboard_support * 0.1
    )
    return relevance, category_match, overlap_score, entity_match, dashboard_support


def score_kpi_relevance(
    *,
    scenario: Any,
    record: Dict[str, Any],
    matched_records: Optional[List[Dict[str, Any]]] = None,
    dashboard_context: Any = None,
    business_context: Any = None,
    scenario_category: Optional[str] = None,
    matched_entities: Any = None,
) -> Dict[str, Any]:
    """Score scenario-to-KPI relevance separately from evidence confidence."""
    scenario_text = _scenario_text(scenario)
    category = str(scenario_category or classify_scenario(scenario)).upper()
    matched = matched_records if isinstance(matched_records, list) else []
    context_text = " ".join(
        _text(value)
        for value in (dashboard_context, business_context)
        if value not in (None, "")
    )
    scenario_terms = _tokens(scenario_text)
    kpi_terms = _tokens(f"{_kpi_name(record)} {_kpi_reasoning(record)}")
    overlap = len(scenario_terms.intersection(kpi_terms))
    context_support = float(bool(kpi_terms.intersection(_tokens(context_text))))
    base_score, category_match, _, entity_support, dashboard_support = _kpi_relevance(
        record,
        scenario_terms,
        matched,
        category,
        matched_entities,
    )
    score = min(1.0, base_score + context_support * 0.1)
    reasons = []
    if category_match:
        reasons.append(f"{classify_kpi(record).title()} KPI aligns with the {category.casefold()} scenario")
    if overlap:
        reasons.append(f"{overlap} scenario term{'s' if overlap != 1 else ''} match the KPI evidence")
    if entity_support:
        reasons.append("matched entity evidence supports the indicator")
    if dashboard_support:
        reasons.append("matched dashboard evidence supports the indicator")
    if context_support:
        reasons.append("business context supports the link")
    return {
        "score": round(score, 3),
        "rationale": "; ".join(reasons) or "No direct scenario, entity, or context link was found",
    }


def build_business_causal_chain(
    scenario: Any,
    scenario_category: str,
    primary_business_entity: str = "",
) -> List[str]:
    """Translate a scenario into downstream business outcomes, not a KPI sequence."""
    text = _scenario_text(scenario).casefold()
    entity = primary_business_entity.strip()
    is_delay = any(
        term in text for term in ("delay", "delayed", "handover", "slippage", "schedule")
    )
    if scenario_category == "OPERATIONAL" and is_delay:
        first = f"{entity} handover delay" if entity else "Project handover delay"
        return [
            first,
            "Customer Commitment Risk",
            "Revenue Recognition Delay",
            "Cashflow Pressure",
            "Enterprise Risk",
        ]
    if scenario_category == "CUSTOMER_EXPERIENCE":
        first = f"{entity} customer experience deterioration" if entity else "Customer Experience Deterioration"
        return [
            first,
            "Customer Retention Risk",
            "Revenue Risk",
            "Enterprise Risk",
        ]
    if scenario_category == "FINANCIAL":
        first = f"{entity} financial pressure" if entity else "Financial Pressure"
        return [
            first,
            "Liquidity Constraint",
            "Investment Capacity Pressure",
            "Enterprise Risk",
        ]
    if scenario_category == "COMPLIANCE":
        first = f"{entity} control or compliance gap" if entity else "Control or Compliance Gap"
        return [
            first,
            "Regulatory or Audit Exposure",
            "Remediation and Penalty Risk",
            "Enterprise Risk",
        ]
    if scenario_category == "STRATEGIC":
        first = f"{entity} strategic delivery pressure" if entity else "Strategic Delivery Pressure"
        return [
            first,
            "Milestone Slippage",
            "Value Realization Delay",
            "Enterprise Risk",
        ]
    first = f"{entity} scenario exposure" if entity else "Scenario Exposure"
    return [first, "Operational and Financial Pressure", "Enterprise Risk"]


def _graph_context(
    graph_summary: Any,
    dependency_paths: Any,
    related_entities: Any,
) -> Tuple[bool, List[str]]:
    summary = graph_summary if isinstance(graph_summary, dict) else {}
    paths = dependency_paths if isinstance(dependency_paths, list) else []
    entities = related_entities if isinstance(related_entities, list) else []
    node_count = summary.get("total_nodes", 0)
    edge_count = summary.get("total_edges", 0)
    has_graph_data = (
        isinstance(node_count, (int, float))
        and isinstance(edge_count, (int, float))
        and (node_count > 0 or edge_count > 0)
    )
    graph_exists = bool(
        has_graph_data
        and summary.get("graph_exists", True)
    )
    if not graph_exists:
        return False, []
    evidence = []
    for path in paths[:2]:
        if not isinstance(path, dict):
            continue
        names = path.get("entities", [])
        relationships = path.get("relationships", [])
        if not isinstance(names, list) or not names:
            continue
        chain = str(names[0])
        for index, name in enumerate(names[1:]):
            edge = (
                f" -[{relationships[index]}]-> "
                if isinstance(relationships, list) and index < len(relationships)
                else " -> "
            )
            chain += edge + str(name)
        evidence.append(_brief(chain, words=22))
    if not evidence:
        names = [
            str(next((item[key] for key in _GRAPH_SUMMARY_KEYS if item.get(key)), ""))
            for item in entities[:3]
            if isinstance(item, dict)
        ]
        if names:
            evidence.append("Related entities: " + ", ".join(names))
    return True, evidence


class CausalReasoningService:
    """Derive domain-agnostic, evidence-linked business impact paths."""

    def analyze(
        self,
        *,
        scenario: Any,
        dashboard_data: Any,
        matched_dashboard_records: Any,
        kpi_insights: Any,
        actions: Any,
        rules: Any,
        impact_result: Any,
        graph_summary: Any = None,
        dependency_paths: Any = None,
        related_entities: Any = None,
        matched_entities: Any = None,
        primary_kpi: Any = None,
        supporting_kpis: Any = None,
    ) -> Dict[str, Any]:
        scenario_text = _scenario_text(scenario)
        matched = matched_dashboard_records if isinstance(matched_dashboard_records, list) else []
        if not matched:
            matched = _records(dashboard_data)
        all_kpis = _records(kpi_insights)
        scenario_category = classify_scenario(scenario, all_kpis)
        selected_kpis = [
            item
            for item in [primary_kpi]
            + (supporting_kpis if isinstance(supporting_kpis, list) else [])
            if isinstance(item, dict) and _kpi_name(item) != "KPI"
        ]
        kpis = selected_kpis
        primary = kpis[0] if kpis else {}
        category = scenario_category
        primary_name = _kpi_name(primary) if primary else ""
        matched_entity_values = (
            matched_entities.get("target_entity", "")
            if isinstance(matched_entities, dict)
            else ""
        )
        if not matched_entity_values and isinstance(scenario, dict):
            matched_entity_values = scenario.get("target_entity", "")
        path = build_business_causal_chain(
            scenario,
            scenario_category,
            str(matched_entity_values or ""),
        )
        graph_available, graph_evidence = _graph_context(
            graph_summary,
            dependency_paths,
            related_entities,
        )

        impact = impact_result if isinstance(impact_result, dict) else {}
        root_causes = RootCauseAnalysisService().analyze(
            scenario=scenario,
            dashboard_data=dashboard_data,
            matched_dashboard_records=matched,
            kpi_insights=kpi_insights,
            rules=rules,
            actions=actions,
            impact_result=impact,
            scenario_category=scenario_category,
        )
        if graph_evidence and root_causes:
            root_causes[0]["evidence"] = list(dict.fromkeys(
                [*root_causes[0].get("evidence", []), *graph_evidence]
            ))[:3]
            root_causes[0]["confidence"] = min(
                0.95,
                round(float(root_causes[0].get("confidence", 0.4)) + 0.05, 2),
            )

        reasoning = _kpi_reasoning(primary) if primary else ""
        value = _kpi_value(primary) if primary else None
        confidence = _confidence(next(
            (primary[key] for key in _CONFIDENCE_KEYS if primary.get(key) is not None),
            None,
        )) if primary else None
        causal_basis = []
        if primary:
            relevance = score_kpi_relevance(
                scenario=scenario,
                record=primary,
                matched_records=matched,
                dashboard_context=dashboard_data,
                scenario_category=scenario_category,
                matched_entities=matched_entities,
            )
            causal_basis.append({
                "kpi": primary_name,
                "category": category,
                "current_value": value,
                "reasoning": _brief(reasoning, words=24),
                "confidence": confidence,
                "relevance_score": relevance["score"],
                "relevance_rationale": relevance["rationale"],
            })
        for record in kpis[1:5]:
            relevance = score_kpi_relevance(
                scenario=scenario,
                record=record,
                matched_records=matched,
                dashboard_context=dashboard_data,
                scenario_category=scenario_category,
                matched_entities=matched_entities,
            )
            causal_basis.append({
                "kpi": _kpi_name(record),
                "category": classify_kpi(record),
                "current_value": _kpi_value(record),
                "reasoning": _brief(_kpi_reasoning(record), words=24),
                "confidence": _confidence(next(
                    (record[key] for key in _CONFIDENCE_KEYS if record.get(key) is not None),
                    None,
                )),
                "relevance_score": relevance["score"],
                "relevance_rationale": relevance["rationale"],
            })
        if graph_evidence:
            causal_basis.append({"source": "Knowledge Graph", "evidence": graph_evidence})

        return {
            "scenario_change": _brief(scenario_text, words=30),
            "scenario_category": scenario_category.casefold(),
            "kpi_relevance": {
                _kpi_name(record): score_kpi_relevance(
                    scenario=scenario,
                    record=record,
                    matched_records=matched,
                    dashboard_context=dashboard_data,
                    scenario_category=scenario_category,
                    matched_entities=matched_entities,
                )
                for record in kpis[:5]
            },
            "primary_kpi": primary_name or None,
            "primary_kpi_category": category,
            "causal_chain": path,
            "primary_impact_path": " → ".join(path),
            "business_consequence": (
                root_causes[0]["business_consequence"]
                if root_causes
                else {
                    "CUSTOMER_EXPERIENCE": "Customer trust and retention may weaken, reducing future demand and revenue.",
                    "FINANCIAL": "Liquidity pressure may constrain investment and funding capacity.",
                    "OPERATIONAL": "Execution disruption may impair service reliability and create downstream financial pressure.",
                    "COMPLIANCE": "Regulatory findings may trigger penalties and reputational consequences.",
                    "STRATEGIC": "Execution gaps may delay value realization and weaken strategic outcomes.",
                    "RISK": "Existing vulnerabilities may increase enterprise and continuity exposure.",
                }.get(scenario_category, "The scenario may create downstream business consequences that require validation."),
            ),
            "causal_basis": causal_basis,
            "graph_evidence": graph_evidence,
            "graph_available": graph_available,
            "confidence": confidence if confidence is not None else (
                0.65 if graph_evidence else 0.4 if primary else 0.25
            ),
            "current_enterprise_problems": [
                {
                    "name": _brief(item.get("name"), words=12),
                    "value": _brief(item.get("formatted_amount"), words=8),
                }
                for item in (
                    impact.get("financial_model", {}).get("current_exposure", {}).get("items", [])
                    if isinstance(impact.get("financial_model"), dict)
                    and isinstance(impact.get("financial_model", {}).get("current_exposure"), dict)
                    else []
                )[:3]
                if isinstance(item, dict)
            ],
            "root_cause_analysis": root_causes[:5],
        }
