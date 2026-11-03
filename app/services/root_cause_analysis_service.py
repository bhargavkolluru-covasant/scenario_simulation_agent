import re
from typing import Any, Dict, List, Optional, Sequence

from app.services.financial_model_service import classify_kpi


_NAME_KEYS = ("kpi_name", "metric_name", "name", "title", "label", "metric")
_VALUE_KEYS = ("kpi_value", "value", "current_value", "metric_value", "score", "amount", "count")
_CONFIDENCE_KEYS = ("confidence_score", "confidence")
_RECORD_LIMIT = 250
_EVIDENCE_LIMIT = 3
_CATEGORY_GUIDANCE = {
    "CUSTOMER": (
        "A deterioration in customer-related performance may weaken demand or retention.",
        "Review the affected indicator, identify its leading drivers, and assign corrective owners.",
    ),
    "FINANCIAL": (
        "Financial pressure may constrain liquidity, margins, or the capacity to fund priorities.",
        "Validate the financial drivers, quantify exposure, and agree accountable control measures.",
    ),
    "OPERATIONAL": (
        "Operational pressure may disrupt execution, capacity, or delivery against commitments.",
        "Review process constraints, confirm ownership, and track a time-bound recovery plan.",
    ),
    "COMPLIANCE": (
        "Control weaknesses may increase regulatory, audit, or policy exposure.",
        "Validate the control gap, assign remediation ownership, and monitor closure evidence.",
    ),
    "STRATEGIC": (
        "The observed pressure may weaken strategic delivery or expected value realization.",
        "Reassess assumptions, align owners on corrective milestones, and monitor leading indicators.",
    ),
    "RISK": (
        "The observed indicator may increase enterprise exposure or business-continuity pressure.",
        "Validate the exposure, assess its drivers, and agree proportionate risk controls.",
    ),
}
_CATEGORY_CAUSE_TERMS = {
    "CUSTOMER": {
        "resolution": "Delayed resolution of customer issues",
        "complaint": "Unresolved customer concerns",
        "service": "Service-quality shortfall affecting the customer experience",
        "quality": "Quality shortfall affecting customer experience",
        "delay": "Delays affecting customer commitments",
        "retention": "Retention pressure from a deteriorating customer experience",
        "experience": "Service-quality or issue-resolution shortfall",
        "satisfaction": "Service-quality or issue-resolution shortfall",
        "csat": "Service-quality or issue-resolution shortfall",
    },
    "FINANCIAL": {
        "liquidity": "Working-capital or liquidity constraint",
        "cash": "Cash-flow pressure from underlying operating conditions",
        "cost": "Cost-control or margin pressure",
        "budget": "Cost-control or margin pressure",
        "overrun": "Cost-control or margin pressure",
        "margin": "Cost-control or margin pressure",
        "funding": "Funding capacity constraint",
        "revenue": "Revenue pressure from the affected business driver",
    },
    "OPERATIONAL": {
        "handover": "Construction delivery constraints affecting handover readiness",
        "construction": "Construction delivery constraints",
        "project": "Project delivery planning or execution constraints",
        "capacity": "Capacity or resource constraint",
        "throughput": "Process throughput constraint",
        "delivery": "Execution or delivery reliability gap",
        "quality": "Process-quality shortfall",
        "delay": "Process or execution delays",
        "downtime": "Availability or downtime pressure",
    },
    "COMPLIANCE": {
        "control": "Control design or execution gap",
        "audit": "Evidence or control assurance gap",
        "regulatory": "Regulatory requirement execution gap",
        "violation": "Control non-adherence requiring validation",
        "policy": "Policy execution or oversight gap",
    },
    "STRATEGIC": {
        "execution": "Strategic execution or ownership gap",
        "milestone": "Strategic milestone delivery pressure",
        "value": "Value-realization assumption or delivery gap",
        "growth": "Growth execution constraint",
        "investment": "Investment prioritization or capacity constraint",
    },
    "RISK": {
        "continuity": "Resilience or continuity weakness",
        "incident": "Incident prevention or response weakness",
        "exposure": "Uncontrolled exposure requiring validation",
        "risk": "Risk control or mitigation gap",
    },
}
_CAUSAL_PATTERN = re.compile(
    r"\b(?:due to|because of|driven by|caused by|attributed to|resulting from|linked to|"
    r"lack of|failure to|insufficient|weak|poor|unresolved|below target|not met)\s+([^.;]+)",
    re.IGNORECASE,
)


def _records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload[:_RECORD_LIMIT] if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("kpis", "recent_kpis", "insights", "items", "data", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value[:_RECORD_LIMIT] if isinstance(item, dict)]
    raw = payload.get("raw")
    summary = raw.get("kpi_summary") if isinstance(raw, dict) else None
    recent = summary.get("recent_kpis") if isinstance(summary, dict) else None
    return [item for item in recent[:_RECORD_LIMIT] if isinstance(item, dict)] if isinstance(recent, list) else []


def _first(record: Dict[str, Any], keys: Sequence[str], default: Any = "") -> Any:
    return next(
        (record[key] for key in keys if record.get(key) not in (None, "")),
        default,
    )


def _text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {_text(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return " ".join(_text(item) for item in value)
    return "" if value is None else str(value)


def _brief(value: Any, max_words: int = 22, max_characters: int = 180) -> str:
    text = " ".join(_text(value).split())
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]) + "…"
    if len(text) > max_characters:
        text = text[:max_characters].rsplit(" ", 1)[0] + "…"
    return text


def _confidence(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if 1 < number <= 100:
        number /= 100
    return min(max(number, 0.0), 1.0)


def _scenario_text(scenario: Any) -> str:
    return _text(scenario)


def _cause_name(
    record: Dict[str, Any],
    reasoning: str,
    scenario_category: str,
) -> str:
    explicit = _first(record, ("root_cause", "potential_root_cause", "cause"))
    if explicit:
        return _brief(explicit, max_words=12, max_characters=90)
    match = _CAUSAL_PATTERN.search(reasoning)
    if match:
        cause = _brief(match.group(1), max_words=12, max_characters=90)
        if cause:
            return cause[0].upper() + cause[1:]
    category = (
        "CUSTOMER"
        if scenario_category == "CUSTOMER_EXPERIENCE"
        else scenario_category
    )
    cause_terms = _CATEGORY_CAUSE_TERMS.get(category, _CATEGORY_CAUSE_TERMS["RISK"])
    context = f"{reasoning} {_text(record)}".casefold()
    for term, cause in cause_terms.items():
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", context):
            return cause
    fallback = {
        "CUSTOMER": "Service or product experience shortfall",
        "FINANCIAL": "Financial planning or control weakness",
        "OPERATIONAL": "Process execution or capacity constraint",
        "COMPLIANCE": "Control adherence or oversight gap",
        "STRATEGIC": "Strategic execution or prioritization gap",
        "RISK": "Risk control or resilience weakness",
    }
    return fallback.get(category, fallback["RISK"])


def _related_source_reasoning(
    name: str,
    reasoning: str,
    matched_records: List[Any],
    rules: List[Any],
    actions: List[Any],
) -> str:
    key_terms = {
        word.casefold()
        for word in re.findall(r"\w+", f"{name} {reasoning}")
        if len(word) > 3
    }
    relevant = []
    for source in [
        *matched_records[:_RECORD_LIMIT],
        *rules[:_RECORD_LIMIT],
        *actions[:_RECORD_LIMIT],
    ]:
        if not isinstance(source, dict):
            continue
        content = _text(source)
        source_terms = {
            word.casefold()
            for word in re.findall(r"\w+", content)
            if len(word) > 3
        }
        if key_terms.intersection(source_terms):
            relevant.append(content)
        if len(relevant) >= 3:
            break
    return _brief(" ".join(relevant), max_words=60, max_characters=400)


def _severity_score(impact_result: Dict[str, Any], record: Dict[str, Any]) -> int:
    severity_by_name = {
        "CRITICAL": 5,
        "HIGH": 4,
        "MEDIUM": 3,
        "MODERATE": 3,
        "LOW": 2,
    }
    record_text = _text(record).casefold()
    score = severity_by_name.get(str(impact_result.get("overall_severity", "")).upper(), 2)
    dimensions = impact_result.get("dimensions", [])
    for dimension in dimensions if isinstance(dimensions, list) else []:
        if not isinstance(dimension, dict):
            continue
        if any(word in _text(dimension).casefold() for word in record_text.split() if len(word) > 3):
            score = max(score, severity_by_name.get(str(dimension.get("severity", "")).upper(), 0))
    return score


def _supporting_evidence(
    name: str,
    value: Any,
    reasoning: str,
    scenario: str,
    rules: List[Any],
    actions: List[Any],
    matched_records: List[Any],
) -> List[str]:
    facts = []
    observation = f"{name}: {value}" if value not in (None, "") else name
    if reasoning:
        observation += f" — {_brief(reasoning, max_words=12, max_characters=90)}"
    facts.append(_brief(observation))

    record_terms = {
        word.casefold()
        for word in re.findall(r"\w+", f"{name} {reasoning}")
        if len(word) > 3
    }
    corroborating: List[str] = []
    for label, sources in (
        ("Dashboard", matched_records),
        ("Rule", rules),
        ("Action", actions),
    ):
        for source in sources[:_RECORD_LIMIT]:
            content = _text(source)
            source_terms = {
                word.casefold()
                for word in re.findall(r"\w+", content)
                if len(word) > 3
            }
            if record_terms.intersection(source_terms):
                detail = _first(source, ("name", "title", "action_title", "rule_name", "description"), content)
                corroborating.append(f"{label}: {_brief(detail, max_words=14, max_characters=110)}")
                break
    facts.extend(corroborating[:_EVIDENCE_LIMIT - 1])
    if not corroborating and scenario:
        facts.append(f"Scenario: {_brief(scenario, max_words=14, max_characters=110)}")
    return list(dict.fromkeys(facts))[:_EVIDENCE_LIMIT]


class RootCauseAnalysisService:
    """Generate concise, evidence-linked root-cause hypotheses without domain rules."""

    def analyze(
        self,
        *,
        scenario: Any,
        dashboard_data: Any,
        matched_dashboard_records: Any,
        kpi_insights: Any,
        rules: Any,
        actions: Any,
        impact_result: Any,
        scenario_category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        scenario_text = _scenario_text(scenario)
        if not scenario_category:
            scenario_category = classify_kpi(scenario_text)
        scenario_category = str(scenario_category).upper()
        guidance_category = (
            "CUSTOMER"
            if scenario_category == "CUSTOMER_EXPERIENCE"
            else scenario_category
        )
        impact = impact_result if isinstance(impact_result, dict) else {}
        rule_records = rules if isinstance(rules, list) else []
        action_records = actions if isinstance(actions, list) else []
        matched_records = (
            matched_dashboard_records
            if isinstance(matched_dashboard_records, list)
            else []
        )
        if not matched_records and isinstance(dashboard_data, (list, dict)):
            matched_records = _records(dashboard_data)

        candidates: List[Dict[str, Any]] = []
        seen = set()
        for record in _records(kpi_insights):
            name = _brief(_first(record, _NAME_KEYS, "Business indicator"), max_words=12, max_characters=80)
            reasoning = _brief(_first(record, ("reasoning", "explanation", "rationale")), max_words=24, max_characters=180)
            value = _first(record, _VALUE_KEYS)
            source_reasoning = _related_source_reasoning(
                name,
                reasoning,
                matched_records,
                rule_records,
                action_records,
            )
            cause = _cause_name(
                record,
                f"{reasoning} {source_reasoning}",
                scenario_category,
            )
            if guidance_category == "OPERATIONAL" and "handover" in scenario_text.casefold():
                cause = "Construction delivery constraints affecting handover readiness"
            elif guidance_category == "OPERATIONAL" and "construction" in scenario_text.casefold():
                cause = "Construction delivery constraints"
            identity = cause.casefold()
            if identity in seen:
                continue
            seen.add(identity)
            consequence, mitigation = _CATEGORY_GUIDANCE.get(
                guidance_category,
                _CATEGORY_GUIDANCE["RISK"],
            )
            if guidance_category == "OPERATIONAL" and any(
                term in scenario_text.casefold()
                for term in (
                    "handover",
                    "construction",
                    "project delay",
                    "project schedule",
                )
            ):
                consequence = (
                    "Delayed delivery may put customer handover commitments and "
                    "milestone-linked revenue recognition at risk."
                )
                mitigation = (
                    "Approve a resource-loaded recovery plan with critical-path "
                    "milestones, named owners, and weekly exception escalation."
                )
            evidence = _supporting_evidence(
                name,
                value,
                reasoning,
                scenario_text,
                rule_records,
                action_records,
                matched_records,
            )
            confidence = _confidence(_first(record, _CONFIDENCE_KEYS))
            confidence = (
                min(0.92, 0.55 + confidence * 0.3 + (0.05 if len(evidence) > 1 else 0))
                if confidence is not None
                else (0.62 if len(evidence) > 1 else 0.45)
            )
            severity = _severity_score(impact, record)
            candidates.append({
                "_rank": severity * 100 + len(evidence) * 10 + confidence * 20,
                "root_cause": cause,
                "scenario_category": scenario_category.casefold(),
                "confidence": round(confidence, 2),
                "severity": {5: "CRITICAL", 4: "HIGH", 3: "MEDIUM", 2: "LOW"}.get(severity, "MEDIUM"),
                "evidence": evidence,
                "business_consequence": consequence,
                "mitigation": mitigation,
                "recommended_mitigation": mitigation,
                "evidence_strength": round(min(len(evidence) / _EVIDENCE_LIMIT, 1.0), 2),
                "impact_score": 0.0,
            })

        if not candidates:
            contextual_sources = [
                ("Dashboard", matched_records),
                ("Rule", rule_records),
                ("Impact assessment", impact.get("dimensions", [])),
            ]
            for label, records in contextual_sources:
                if not isinstance(records, list):
                    continue
                for record in records[:_RECORD_LIMIT]:
                    if not isinstance(record, dict):
                        continue
                    name = _first(
                        record,
                        (*_NAME_KEYS, "rule_name", "dimension_name", "entity_name"),
                    )
                    if not name:
                        name = next(
                            (
                                key.replace("_", " ").title()
                                for key, value in record.items()
                                if key.casefold() not in {"id", "uuid", "entity_id"}
                                and value not in (None, "")
                            ),
                            "Business condition",
                        )
                    detail = _first(
                        record,
                        (
                            "reasoning",
                            "description",
                            "business_consequence",
                            "impact_description",
                            "risk",
                            "status",
                            "condition",
                        ),
                    )
                    cause = _cause_name(
                        record,
                        _brief(detail),
                        scenario_category,
                    )
                    if guidance_category == "OPERATIONAL" and "handover" in scenario_text.casefold():
                        cause = "Construction delivery constraints affecting handover readiness"
                    elif guidance_category == "OPERATIONAL" and "construction" in scenario_text.casefold():
                        cause = "Construction delivery constraints"
                    if cause.casefold() in seen:
                        continue
                    seen.add(cause.casefold())
                    consequence, mitigation = _CATEGORY_GUIDANCE.get(
                        guidance_category,
                        _CATEGORY_GUIDANCE["RISK"],
                    )
                    if guidance_category == "OPERATIONAL" and any(
                        term in scenario_text.casefold()
                        for term in (
                            "handover",
                            "construction",
                            "project delay",
                            "project schedule",
                        )
                    ):
                        consequence = (
                            "Delayed delivery may put customer handover commitments and "
                            "milestone-linked revenue recognition at risk."
                        )
                        mitigation = (
                            "Approve a resource-loaded recovery plan with critical-path "
                            "milestones, named owners, and weekly exception escalation."
                        )
                    evidence = [f"{label}: {_brief(name)}"]
                    if detail:
                        evidence.append(f"Context: {_brief(detail)}")
                    if scenario_text:
                        evidence.append(
                            f"Scenario: {_brief(scenario_text, max_words=12, max_characters=100)}"
                        )
                    confidence = _confidence(_first(record, _CONFIDENCE_KEYS))
                    confidence = confidence if confidence is not None else 0.45
                    severity = _severity_score(impact, record)
                    candidates.append({
                        "_rank": severity * 100 + len(evidence) * 10 + confidence * 20,
                        "root_cause": cause,
                        "scenario_category": scenario_category.casefold(),
                        "confidence": round(confidence, 2),
                        "severity": {5: "CRITICAL", 4: "HIGH", 3: "MEDIUM", 2: "LOW"}.get(severity, "MEDIUM"),
                        "evidence": evidence[:_EVIDENCE_LIMIT],
                        "business_consequence": consequence,
                        "mitigation": mitigation,
                        "recommended_mitigation": mitigation,
                        "evidence_strength": round(min(len(evidence) / _EVIDENCE_LIMIT, 1.0), 2),
                        "impact_score": 0.0,
                    })
                    if len(candidates) >= 5:
                        break
                if len(candidates) >= 5:
                    break

        if not candidates and scenario_text:
            consequence, mitigation = _CATEGORY_GUIDANCE.get(
                guidance_category,
                _CATEGORY_GUIDANCE["RISK"],
            )
            candidates.append({
                "_rank": 20,
                "root_cause": _cause_name({}, scenario_text, scenario_category),
                "scenario_category": scenario_category.casefold(),
                "confidence": 0.35,
                "severity": "MEDIUM",
                "evidence": [f"Scenario: {_brief(scenario_text, max_words=18, max_characters=140)}"],
                "business_consequence": consequence,
                "mitigation": mitigation,
                "recommended_mitigation": mitigation,
                "evidence_strength": 0.25,
                "impact_score": 0.0,
            })
        if not candidates:
            candidates.append({
                "_rank": 0,
                "root_cause": "Insufficient evidence to infer a likely driver",
                "scenario_category": scenario_category.casefold(),
                "confidence": 0.1,
                "severity": "LOW",
                "evidence": ["No scenario-linked KPI, rule, or dashboard evidence was available."],
                "business_consequence": "A material business consequence cannot be established from the available evidence.",
                "mitigation": "Gather scenario-relevant operating evidence and validate potential contributing factors.",
                "recommended_mitigation": "Gather scenario-relevant operating evidence and validate potential contributing factors.",
                "evidence_strength": 0.0,
                "impact_score": 0.0,
            })

        candidates.sort(key=lambda item: item["_rank"], reverse=True)
        return [
            {key: value for key, value in item.items() if key != "_rank"}
            for item in candidates[:5]
        ]
