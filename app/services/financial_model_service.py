import re
from typing import Any, Dict, Iterable, List, Optional, Tuple


_NAME_KEYS = (
    "kpi_name",
    "metric_name",
    "name",
    "title",
    "label",
    "metric",
    "description",
)
_TEXT_KEYS = (
    *_NAME_KEYS,
    "reasoning",
    "explanation",
    "rationale",
    "labels",
    "category",
    "classification",
    "business_context",
)
_VALUE_KEYS = (
    "kpi_value",
    "value",
    "current_value",
    "metric_value",
    "amount",
    "score",
    "count",
)
_CONFIDENCE_KEYS = ("confidence_score", "confidence")
_IMPORTANCE_KEYS = ("business_importance", "importance", "materiality", "priority", "weight")
_CURRENCIES = ("AED", "USD", "EUR", "GBP")
_CATEGORY_TERMS = {
    "CUSTOMER": (
        "customer", "client", "satisfaction", "experience", "retention",
        "complaint", "loyalty", "churn", "service quality", "csat",
    ),
    "FINANCIAL": (
        "financial", "revenue", "income", "cost", "expense", "profit",
        "margin", "cash", "liquidity", "balance", "receivable", "payable",
        "debt", "budget", "capital", "expenditure", "earnings",
    ),
    "OPERATIONAL": (
        "operational", "throughput", "capacity", "productivity", "efficiency",
        "downtime", "delay", "cycle time", "output", "utilization", "delivery",
        "quality", "inventory", "shortage", "yield", "availability",
    ),
    "COMPLIANCE": (
        "compliance", "regulatory", "violation", "audit", "control",
        "policy", "legal", "penalty", "adherence", "inspection",
    ),
    "RISK": (
        "risk", "exposure", "incident", "loss", "threat", "continuity",
        "resilience", "vulnerability", "severity", "mitigation",
    ),
    "STRATEGIC": (
        "strategic", "strategy", "growth", "market share", "objective",
        "investment", "transformation", "portfolio", "competitive",
        "value realization",
    ),
}
_CATEGORY_PRIORITY = (
    "COMPLIANCE",
    "CUSTOMER",
    "FINANCIAL",
    "OPERATIONAL",
    "STRATEGIC",
    "RISK",
)
IMPACT_MODEL_REGISTRY = {
    "CUSTOMER": ("Revenue Risk", "Retention Risk", "Demand Risk"),
    "FINANCIAL": ("Liquidity Risk", "Cash Flow Risk", "Profitability Risk"),
    "OPERATIONAL": ("Execution Risk", "Delay Risk", "Capacity Risk"),
    "COMPLIANCE": ("Penalty Risk", "Regulatory Risk", "Audit Risk"),
    "RISK": ("Enterprise Risk", "Business Continuity Risk"),
    "STRATEGIC": ("Growth Risk", "Strategic Delivery Risk", "Value Realization Risk"),
}
_DIRECTION_TERMS = {
    "INCREASE": ("increase", "increases", "increasing", "rise", "rises", "rising", "grow", "growth", "higher", "up", "escalate", "escalation"),
    "DECREASE": ("decrease", "decreases", "decreasing", "fall", "falls", "falling", "decline", "declines", "declining", "reduce", "reduction", "lower", "down", "drop", "drops", "dropped"),
    "DELAY": ("delay", "delays", "delayed", "slower", "late", "postpone", "postponed"),
}
_ADVERSE_TERMS = (
    "delay", "slower", "late", "shortage", "decline", "fall", "reduction",
    "drop", "worsen", "deteriorate", "failure", "breach", "violation",
)
_RISK_SIGNAL_TERMS = (
    "risk", "exposure", "incident", "violation", "overdue", "shortage",
    "delay", "error", "defect", "loss", "cost", "complaint", "downtime",
    "failure", "breach", "overrun", "variance", "unpaid", "outstanding",
)
_PERFORMANCE_TERMS = (
    "revenue", "profit", "throughput", "capacity", "productivity",
    "satisfaction", "quality", "availability", "growth", "output",
    "efficiency", "yield", "cash flow", "margin", "balance",
)
_GENERIC_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "could", "does", "during",
    "fall", "falls", "for", "from", "if", "in", "increase", "increases", "into",
    "is", "it", "of", "on", "or", "should", "that", "the", "this", "to", "what",
    "when", "will", "with", "would", "decrease", "decreases", "drop", "drops",
    "rise", "rises", "decline", "declines", "increase", "increased", "decreased",
}


def _text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {_text(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_text(item) for item in value)
    return "" if value is None else str(value)


def _scenario_text(scenario: Any) -> str:
    if not isinstance(scenario, dict):
        return _text(scenario)
    preferred_keys = (
        "query",
        "description",
        "change_type",
        "direction",
        "target_entity",
        "scenario_type",
        "domain",
        "change_percentage",
        "change_amount",
        "time_horizon",
    )
    parts = [
        _text(scenario[key])
        for key in preferred_keys
        if scenario.get(key) not in (None, "")
    ]
    return " ".join(parts) or _text(scenario)


def _record_text(record: Dict[str, Any]) -> str:
    return " ".join(
        _text(record.get(key))
        for key in _TEXT_KEYS
        if record.get(key) not in (None, "")
    )


def classify_kpi(kpi: Any) -> str:
    """Classify KPI evidence using its semantic labels and explanatory text."""
    if isinstance(kpi, str):
        text = kpi.casefold()
        explicit_category = ""
    elif isinstance(kpi, dict):
        text = _record_text(kpi).casefold()
        explicit_category = str(
            kpi.get("category") or kpi.get("classification") or ""
        ).strip().upper()
    else:
        return "RISK"

    explicit_category = re.sub(r"[^A-Z]", "", explicit_category)
    if explicit_category in IMPACT_MODEL_REGISTRY:
        return explicit_category

    scores = {
        category: sum(
            1 for term in terms
            if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text)
        )
        for category, terms in _CATEGORY_TERMS.items()
    }
    return max(
        _CATEGORY_PRIORITY,
        key=lambda category: (scores[category], -_CATEGORY_PRIORITY.index(category)),
    ) if any(scores.values()) else "RISK"


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(
            r"(?P<number>-?\d[\d,]*(?:\.\d+)?)\s*(?P<scale>[KMB])?",
            value,
            re.IGNORECASE,
        )
        if not match:
            return None
        amount = float(match.group("number").replace(",", ""))
        scale = (match.group("scale") or "").upper()
        return amount * {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(scale, 1)
    return None


def _records(payload: Any) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if any(key in value for key in (*_NAME_KEYS, *_VALUE_KEYS)):
                result.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return result


def _record_name(record: Dict[str, Any]) -> str:
    return next(
        (str(record[key]) for key in _NAME_KEYS if record.get(key) not in (None, "")),
        "Unlabeled KPI",
    )


def _record_value(record: Dict[str, Any]) -> Any:
    return next(
        (record[key] for key in _VALUE_KEYS if record.get(key) not in (None, "")),
        None,
    )


def _confidence(record: Dict[str, Any]) -> float:
    raw = next(
        (record.get(key) for key in _CONFIDENCE_KEYS if record.get(key) not in (None, "")),
        None,
    )
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.5
    if value > 1:
        value /= 100
    return min(max(value, 0.0), 1.0)


def _importance(record: Dict[str, Any]) -> float:
    raw = next(
        (record.get(key) for key in _IMPORTANCE_KEYS if record.get(key) not in (None, "")),
        None,
    )
    if isinstance(raw, str):
        levels = {"CRITICAL": 1.0, "HIGH": 0.85, "MEDIUM": 0.6, "LOW": 0.35}
        if raw.upper() in levels:
            return levels[raw.upper()]
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.6
    if value > 1:
        value /= 100
    return min(max(value, 0.0), 1.0)


def _currency(value: Any, unit: Any = None) -> str:
    text = f"{value or ''} {unit or ''}".upper()
    for code in _CURRENCIES:
        if code in text:
            return code
    return {"$": "USD", "€": "EUR", "£": "GBP"}.get(
        next((symbol for symbol in ("$", "€", "£") if symbol in text), ""),
        "",
    )


def _money(record: Dict[str, Any]) -> Optional[Tuple[float, str]]:
    value = _record_value(record)
    unit = record.get("kpi_unit") or record.get("unit") or record.get("uom")
    currency = _currency(value, unit)
    if not currency or "%" in str(value) or "%" in str(unit):
        return None
    amount = _number(value)
    if amount is None:
        return None
    unit_text = str(unit or "").casefold()
    if not re.search(r"[KMB]\b", str(value), re.IGNORECASE):
        if "billion" in unit_text:
            amount *= 1_000_000_000
        elif "million" in unit_text:
            amount *= 1_000_000
        elif "thousand" in unit_text:
            amount *= 1_000
    return amount, currency


def _format_money(amount: float, currency: str) -> str:
    return f"{currency} {amount:,.2f}".rstrip("0").rstrip(".")


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", text.casefold())
        if len(token) > 2 and token not in _GENERIC_WORDS
    }


def _direction(scenario_text: str, scenario: Any) -> str:
    structured = scenario.get("change_type") if isinstance(scenario, dict) else None
    text = f"{structured or ''} {scenario_text}".casefold()
    for direction, terms in _DIRECTION_TERMS.items():
        if any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms):
            return direction
    pair = re.search(
        r"\bfrom\s+(-?\d[\d,]*(?:\.\d+)?)\s+to\s+(-?\d[\d,]*(?:\.\d+)?)\b",
        scenario_text,
        re.IGNORECASE,
    )
    if pair:
        initial = float(pair.group(1).replace(",", ""))
        target = float(pair.group(2).replace(",", ""))
        return "INCREASE" if target > initial else "DECREASE" if target < initial else "UNKNOWN"
    return "UNKNOWN"


def _magnitude(scenario_text: str, scenario: Any) -> Optional[float]:
    structured = scenario.get("change_percentage") if isinstance(scenario, dict) else None
    value = _number(structured)
    if value is not None and value != 0:
        return abs(value)
    percent = re.search(r"(-?\d+(?:\.\d+)?)\s*%", scenario_text)
    if percent:
        return abs(float(percent.group(1)))
    pair = re.search(
        r"\bfrom\s+(-?\d[\d,]*(?:\.\d+)?)\s+to\s+(-?\d[\d,]*(?:\.\d+)?)\b",
        scenario_text,
        re.IGNORECASE,
    )
    if pair:
        initial = float(pair.group(1).replace(",", ""))
        target = float(pair.group(2).replace(",", ""))
        if initial:
            return abs((target - initial) / initial * 100)
    return None


def _severity(magnitude: Optional[float], scenario_text: str) -> str:
    text = scenario_text.casefold()
    for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        if re.search(rf"\b{level.casefold()}\b", text):
            return level
    if magnitude is None:
        return "MEDIUM"
    if magnitude >= 30:
        return "CRITICAL"
    if magnitude >= 15:
        return "HIGH"
    if magnitude >= 5:
        return "MEDIUM"
    return "LOW"


def _severity_value(level: str) -> int:
    return {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}.get(level, 1)


def _adjust_severity(level: str, confidence: float, importance: float) -> str:
    level_value = _severity_value(level)
    evidence_weight = 0.5 + 0.25 * confidence + 0.25 * importance
    if evidence_weight >= 0.85:
        level_value = min(level_value + 1, 4)
    elif evidence_weight <= 0.65:
        level_value = max(level_value - 1, 1)
    return {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}[level_value]


def _is_adverse(
    scenario_text: str,
    direction: str,
    affected: Iterable[Dict[str, Any]],
) -> bool:
    lowered = scenario_text.casefold()
    if any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in _ADVERSE_TERMS):
        return True
    if direction == "DELAY":
        return True
    records_text = " ".join(
        _record_text(item["record"]).casefold()
        for item in affected
        if isinstance(item.get("record"), dict)
    )
    if direction == "INCREASE":
        return any(term in f"{lowered} {records_text}" for term in _RISK_SIGNAL_TERMS)
    if direction == "DECREASE":
        return any(term in records_text for term in _PERFORMANCE_TERMS)
    return False


def _current_exposure(record: Dict[str, Any]) -> bool:
    text = _record_text(record).casefold()
    indicators = (
        "risk", "exposure", "overdue", "outstanding", "unpaid", "variance",
        "overrun", "loss", "liability", "penalty", "debt", "arrears",
        "impairment", "deficit", "pending", "unsettled", "unresolved",
    )
    return any(term in text for term in indicators)


def _match_score(scenario_tokens: set[str], record: Dict[str, Any]) -> float:
    record_tokens = _tokens(_record_text(record))
    if not scenario_tokens or not record_tokens:
        return 0.0
    overlap = scenario_tokens & record_tokens
    return len(overlap) / max(len(scenario_tokens), 1)


def _scenario_categories(scenario_text: str) -> List[str]:
    category = classify_kpi(scenario_text)
    return [category]


def _combine_severity(levels: Iterable[str]) -> str:
    max_value = max((_severity_value(level) for level in levels), default=0)
    return {0: "UNQUANTIFIED", 1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}[max_value]


class FinancialModelService:
    """Build a domain-agnostic impact assessment from KPI and scenario evidence."""

    def classify_kpi(self, kpi: Any) -> str:
        return classify_kpi(kpi)

    def model(
        self,
        *,
        scenario: Any,
        dashboard_data: Any,
        kpi_insights: Any,
        actions: Any,
        rules: Any,
    ) -> Dict[str, Any]:
        del actions, rules
        scenario_text = _scenario_text(scenario)
        direction = _direction(scenario_text, scenario)
        magnitude = _magnitude(scenario_text, scenario)
        scenario_severity = _severity(magnitude, scenario_text)
        adverse = False
        scenario_tokens = _tokens(scenario_text)
        kpi_records = _records(kpi_insights)
        dashboard_records = _records(dashboard_data)

        exposures = []
        seen_exposures = set()
        for source, records in (
            ("KPI evidence", kpi_records),
            ("Dashboard evidence", dashboard_records),
        ):
            for record in records:
                category = classify_kpi(record)
                money = _money(record)
                if not money or money[0] <= 0 or not _current_exposure(record):
                    continue
                amount, currency = money
                key = (_record_name(record).casefold(), round(amount, 2), currency)
                if key in seen_exposures:
                    continue
                seen_exposures.add(key)
                exposures.append({
                    "name": _record_name(record),
                    "amount": round(amount, 2),
                    "currency": currency,
                    "formatted_amount": _format_money(amount, currency),
                    "category": category,
                    "confidence": _confidence(record),
                    "source": source,
                    "classification": "Current Enterprise Exposure",
                })
        exposures.sort(key=lambda item: item["amount"], reverse=True)
        current_totals: Dict[str, float] = {}
        for exposure in exposures:
            currency = exposure["currency"]
            current_totals[currency] = current_totals.get(currency, 0.0) + exposure["amount"]
        current_exposure = {
            "items": exposures[:20],
            "total_by_currency": {
                currency: round(amount, 2)
                for currency, amount in current_totals.items()
            },
            "description": (
                "Current financial risk indicators are existing conditions, not scenario-caused losses."
            ),
        }

        categorized_records = []
        seen_records = set()
        for source, records in (
            ("KPI evidence", kpi_records),
            ("Dashboard evidence", dashboard_records),
        ):
            for record in records:
                value = _number(_record_value(record))
                if value is None:
                    continue
                category = classify_kpi(record)
                dedupe_key = (_record_name(record).casefold(), value, category)
                if dedupe_key in seen_records:
                    continue
                seen_records.add(dedupe_key)
                match_score = _match_score(scenario_tokens, record)
                categorized_records.append({
                    "record": record,
                    "source": source,
                    "category": category,
                    "value": value,
                    "match_score": match_score,
                })

        matched = [item for item in categorized_records if item["match_score"] > 0]
        if not matched:
            inferred_categories = _scenario_categories(scenario_text)
            matched = [
                item for item in categorized_records
                if item["category"] in inferred_categories
            ]
        matched.sort(
            key=lambda item: (
                item["match_score"],
                _confidence(item["record"]),
                _importance(item["record"]),
            ),
            reverse=True,
        )
        affected = matched[:10]
        adverse = _is_adverse(scenario_text, direction, affected)
        affected_categories = list(dict.fromkeys(
            item["category"] for item in affected
        )) or _scenario_categories(scenario_text)
        if not adverse:
            scenario_severity = "LOW" if direction in {"INCREASE", "DECREASE"} else "UNQUANTIFIED"

        evidence_confidences = [
            _confidence(item["record"]) for item in affected
        ]
        evidence_importance = [
            _importance(item["record"]) for item in affected
        ]
        if evidence_confidences:
            evidence_confidence = sum(evidence_confidences) / len(evidence_confidences)
        else:
            evidence_confidence = 0.35
        importance = (
            sum(evidence_importance) / len(evidence_importance)
            if evidence_importance
            else 0.5
        )
        match_quality = (
            sum(item["match_score"] for item in affected) / len(affected)
            if affected
            else 0.25
        )
        confidence = round(
            min(max(evidence_confidence * (0.65 + 0.2 * importance + 0.15 * match_quality), 0.0), 1.0),
            3,
        )

        impacts = []
        category_severities = []
        for category in affected_categories:
            if scenario_severity == "UNQUANTIFIED":
                continue
            models = IMPACT_MODEL_REGISTRY.get(category, IMPACT_MODEL_REGISTRY["RISK"])
            level = scenario_severity
            if not affected:
                level = "LOW" if scenario_severity == "UNQUANTIFIED" else scenario_severity
            else:
                category_items = [
                    item for item in affected if item["category"] == category
                ]
                category_confidence = sum(
                    _confidence(item["record"]) for item in category_items
                ) / len(category_items)
                category_importance = sum(
                    _importance(item["record"]) for item in category_items
                ) / len(category_items)
                level = _adjust_severity(
                    level,
                    category_confidence,
                    category_importance,
                )
            category_severities.append(level)
            impacts.extend({
                "category": category,
                "impact": name,
                "severity": level,
                "direction": direction,
            } for name in models)

        estimated_amounts: Dict[str, float] = {}
        amount_evidence = []
        if adverse and magnitude is not None:
            for item in affected:
                record = item["record"]
                money = _money(record)
                if money is None or item["match_score"] <= 0:
                    continue
                amount, currency = money
                estimated = round(abs(amount) * magnitude / 100, 2)
                if estimated <= 0:
                    continue
                estimated_amounts[currency] = estimated_amounts.get(currency, 0.0) + estimated
                amount_evidence.append({
                    "kpi": _record_name(record),
                    "baseline": _format_money(amount, currency),
                    "estimated_scenario_amount": _format_money(estimated, currency),
                    "scenario_change_percent": round(magnitude, 2),
                    "confidence": _confidence(record),
                    "why": (
                        f"{_record_name(record)} is directly matched to the scenario and provides "
                        "the monetary baseline used for this estimate."
                    ),
                    "derivation": (
                        f"{_format_money(amount, currency)} × "
                        f"{magnitude:.2f}% = {_format_money(estimated, currency)}"
                    ),
                    "assumptions": [
                        "The explicit scenario percentage applies proportionally to this matched monetary KPI.",
                        "This is an indicative scenario estimate, not a realized loss or validated causal forecast.",
                    ],
                })

        drivers = [
            {
                "kpi": _record_name(item["record"]),
                "category": item["category"],
                "current_value": _record_value(item["record"]),
                "unit": item["record"].get("kpi_unit")
                or item["record"].get("unit")
                or item["record"].get("uom"),
                "reasoning": item["record"].get("reasoning")
                or item["record"].get("explanation")
                or item["record"].get("rationale"),
                "confidence": _confidence(item["record"]),
                "business_importance": _importance(item["record"]),
                "match_score": round(item["match_score"], 3),
            }
            for item in affected
        ]
        scenario_exposure = {
            "direction": direction,
            "severity": _combine_severity(category_severities) if adverse else scenario_severity,
            "confidence": confidence,
            "affected_categories": affected_categories,
            "impacts": impacts,
            "impact_drivers": drivers,
            "estimated_amount_by_currency": {
                currency: round(amount, 2)
                for currency, amount in estimated_amounts.items()
            },
            "amount_evidence": amount_evidence,
            "financial_reasoning": (
                (
                    "Each monetary estimate uses a directly scenario-matched monetary KPI baseline "
                    "multiplied by the explicit scenario percentage; see amount evidence for the baseline, "
                    "calculation, and assumptions. "
                    if amount_evidence
                    else ""
                )
                + "Scenario risk is derived from the parsed direction and magnitude, affected KPI evidence, "
                "KPI confidence, and business-importance signals. Monetary estimates are included only "
                "where an affected monetary KPI and explicit scenario percentage are both available."
            ),
            "assumptions": [
                "Explicit percentage changes are applied proportionally to directly matched monetary KPI baselines; this is a directional estimate, not a causal forecast.",
                "Qualitative scenarios receive a severity assessment but no invented monetary amount.",
                "When a KPI omits confidence or business importance, conservative neutral defaults are used and reduce certainty.",
            ],
        }
        combined_outlook = {
            "severity": _combine_severity(
                [item["severity"] for item in impacts]
                + ([scenario_severity] if scenario_severity != "UNQUANTIFIED" else [])
            ),
            "risk_dimensions": impacts,
            "summary": (
                "Combined outlook is a qualitative assessment of existing enterprise risks and "
                "incremental scenario risk; the monetary amounts are not added together."
            ),
        }
        return {
            "current_exposure": current_exposure,
            "scenario_exposure": scenario_exposure,
            "combined_outlook": combined_outlook,
            "confidence": confidence,
        }
