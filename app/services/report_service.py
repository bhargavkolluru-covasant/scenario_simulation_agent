import datetime
import re
import uuid
from typing import Any, Dict, List, Set
from zoneinfo import ZoneInfo


_KPI_VALUE_KEYS = (
    "value",
    "kpi_value",
    "raw_value",
    "current_value",
    "metric_value",
    "statistic_value",
    "score",
    "amount",
    "count",
)
_ACTUAL_KEYS = ("latest_actual", "actual", "actual_value")
_FORECAST_KEYS = ("latest_forecast", "forecast", "forecast_value")
_VARIANCE_KEYS = ("variance", "variance_value", "variance_amount")
_KPI_NAME_KEYS = (
    "kpi_name",
    "metric_name",
    "statistic_name",
    "name",
    "title",
    "label",
    "metric",
)
_PROJECT_KEYS = ("project", "project_name", "property", "entity", "asset")
_HANDOVER_DATE_KEYS = (
    "target_handover",
    "target_handover_date",
    "handover_target",
    "planned_handover_date",
    "handover_date",
    "expected_handover_date",
    "target_date",
)
_STATUS_KEYS = ("status", "project_status", "construction_status", "lifecycle_status")
_LOCATION_KEYS = ("location", "city", "emirate", "area")
_IRRELEVANT_WORDS = {
    "about", "after", "against", "along", "also", "and", "are", "because",
    "business", "could", "from", "have", "into", "more", "only", "over",
    "risk", "scenario", "selected", "should", "that", "their", "there",
    "these", "this", "through", "under", "using", "what", "when", "where",
    "which", "while", "with", "would",
}


def _display_text(value: Any, default: str = "") -> str:
    text = _text(value, default)
    text = re.sub(
        r"\bHighest\s+Benefit\s+Unit\b",
        "Highest and Best Use (HBU)",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"\bHighest\s+Best\s+Use(?:\s*\(HBU\))?\b",
        "Highest and Best Use (HBU)",
        text,
        flags=re.IGNORECASE,
    )


def _sentence(value: Any) -> str:
    text = _display_text(value).strip().rstrip(".!?")
    return f"{text}." if text else ""


def _lower_first(value: Any) -> str:
    text = _display_text(value)
    return text[:1].lower() + text[1:] if text else ""


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _display_query(value: Any) -> str:
    words = _display_text(value, "Scenario assessment").split()
    display_words = []
    for word in words:
        if display_words and display_words[-1].rstrip(".,;:!?").casefold() == word.rstrip(
            ".,;:!?"
        ).casefold():
            continue
        display_words.append(word)
    return re.sub(r"\s+", " ", " ".join(display_words)).strip()


def _decision_items(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _item_name(item: Dict[str, Any], default: str) -> str:
    return _display_text(
        item.get("name")
        or item.get("kpi_name")
        or item.get("risk_name")
        or item.get("title")
        or item.get("action_title")
        or item.get("action"),
        default,
    )


def _normalized(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", _text(value).casefold()))


def _row_name(item: Dict[str, Any]) -> str:
    return next(
        (
            _text(item[key])
            for key in _KPI_NAME_KEYS
            if item.get(key) not in (None, "")
        ),
        "",
    )


def _value_details(item: Dict[str, Any]) -> List[tuple[str, Any]]:
    details: List[tuple[str, Any]] = []
    for key in _KPI_VALUE_KEYS:
        value = item.get(key)
        if value not in (None, "") and _text(value):
            label = {
                "current_value": "Current",
                "metric_value": "Statistic",
                "statistic_value": "Statistic",
                "raw_value": "Value",
            }.get(key, "Value")
            details.append((label, value))
            break
    for label, keys in (
        ("Latest Actual", _ACTUAL_KEYS),
        ("Latest Forecast", _FORECAST_KEYS),
        ("Variance", _VARIANCE_KEYS),
    ):
        value = next((item[key] for key in keys if item.get(key) not in (None, "")), None)
        if value is not None and _text(value):
            details.append((label, value))
    return details


def _dashboard_records(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    seen: Set[int] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            identity = id(value)
            if identity in seen:
                return
            seen.add(identity)
            records.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            identity = id(value)
            if identity in seen:
                return
            seen.add(identity)
            for child in value:
                visit(child)

    for key in (
        "dashboard_rows",
        "widget_rows",
        "widget_data",
        "table_records",
        "stat_cards",
        "chart_series",
        "dashboard_data",
        "dashboard_definition",
    ):
        visit(state.get(key))
    return records


def _series_latest_value(value: Any) -> Any:
    if not isinstance(value, list):
        return value if value not in (None, "") else None
    for point in reversed(value):
        if isinstance(point, dict):
            candidate = next(
                (
                    point[key]
                    for key in ("value", "y", "actual", "forecast", "count", "amount")
                    if point.get(key) not in (None, "")
                ),
                None,
            )
            if candidate is not None:
                return candidate
        elif point not in (None, ""):
            return point
    return None


def _details_for_name(name: str, records: List[Dict[str, Any]]) -> List[tuple[str, Any]]:
    normalized_name = _normalized(name)
    if not normalized_name:
        return []

    for record in records:
        row_name = _normalized(_row_name(record))
        if row_name and (
            row_name == normalized_name
            or row_name in normalized_name
            or normalized_name in row_name
        ):
            details = _value_details(record)
            if details:
                return details

    for record in records:
        for key, value in record.items():
            if (
                _normalized(key) == normalized_name
                and value not in (None, "")
                and not isinstance(value, (dict, list))
            ):
                return [("Value", value)]
    return []


def _handover_details(records: List[Dict[str, Any]]) -> List[tuple[str, Any]]:
    details: List[tuple[str, Any]] = []
    for label, keys in (
        ("Project", _PROJECT_KEYS),
        ("Location", _LOCATION_KEYS),
        ("Target Handover", _HANDOVER_DATE_KEYS),
        ("Status", _STATUS_KEYS),
    ):
        value = next(
            (
                record[key]
                for record in records
                for key in keys
                if record.get(key) not in (None, "")
                and not isinstance(record.get(key), (dict, list))
            ),
            None,
        )
        if value is not None:
            details.append((label, value))
    if not any(label == "Project" for label, _ in details):
        project_name = next(
            (
                record["name"]
                for record in records
                if record.get("name") not in (None, "")
                and any(
                    record.get(key) not in (None, "")
                    for key in (*_HANDOVER_DATE_KEYS, *_STATUS_KEYS, *_LOCATION_KEYS)
                )
            ),
            None,
        )
        if project_name is not None:
            details.insert(0, ("Project", project_name))
    return details


def _market_details(records: List[Dict[str, Any]]) -> List[tuple[str, Any]]:
    count_keys = (
        "current_launch_count",
        "launch_count",
        "competitor_launches",
        "current_count",
    )
    count = next(
        (
            record[key]
            for record in records
            for key in count_keys
            if record.get(key) not in (None, "")
            and not isinstance(record.get(key), (dict, list))
        ),
        None,
    )
    if count is not None:
        return [("Current Launch Count", count)]
    series_count = next(
        (
            value
            for record in records
            if any(
                term in _normalized(_row_name(record))
                for term in ("competitor", "launch")
            )
            for value in [
                _series_latest_value(record.get("data") or record.get("values"))
            ]
            if value is not None
        ),
        None,
    )
    if series_count is not None:
        return [("Current Launch Count", series_count)]

    observation_keys = (
        "observation",
        "current_observation",
        "dashboard_observation",
        "summary",
        "description",
    )
    observation = next(
        (
            record[key]
            for record in records
            for key in observation_keys
            if record.get(key) not in (None, "")
            and not isinstance(record.get(key), (dict, list))
        ),
        None,
    )
    return [("Current Dashboard Observation", observation)] if observation is not None else []


def _dashboard_kpi_details(
    item: Dict[str, Any],
    records: List[Dict[str, Any]],
) -> List[tuple[str, Any]]:
    name = _item_name(item, "")
    normalized = name.casefold()
    if "handover" in normalized or "nearing handover" in normalized:
        project_details = _handover_details(records)
        count_details = _details_for_name(name, records)
        project_details.extend(
            ("Current Count" if label == "Value" else label, value)
            for label, value in count_details
        )
        return project_details
    if "cashflow" in normalized or "cash flow" in normalized or "forecast" in normalized:
        metric_details = _details_for_name(name, records)
        if any(
            label in {"Latest Actual", "Latest Forecast", "Variance"}
            for label, _ in metric_details
        ):
            return metric_details
        return _finance_details(records)

    details = _details_for_name(name, records)
    if details:
        if "competitor" in normalized or "launch" in normalized:
            return [
                (
                    "Current Launch Count"
                    if label in {"Value", "Statistic", "Current"}
                    else label,
                    value,
                )
                for label, value in details
            ]
        return details
    if "competitor" in normalized or "launch" in normalized:
        return _market_details(records)
    return []


def _finance_details(records: List[Dict[str, Any]]) -> List[tuple[str, Any]]:
    details: List[tuple[str, Any]] = []
    for label, keys in (
        ("Latest Actual", _ACTUAL_KEYS),
        ("Latest Forecast", _FORECAST_KEYS),
        ("Variance", _VARIANCE_KEYS),
    ):
        value = next(
            (
                record[key]
                for record in records
                for key in keys
                if record.get(key) not in (None, "")
                and not isinstance(record.get(key), (dict, list))
            ),
            None,
        )
        if value is None:
            series_name = {
                "Latest Actual": "actual",
                "Latest Forecast": "forecast",
                "Variance": "variance",
            }[label]
            value = next(
                (
                    candidate
                    for record in records
                    if _normalized(_row_name(record)) in {
                        series_name, f"latest {series_name}"
                    }
                    for candidate in [
                        _series_latest_value(record.get("data") or record.get("values"))
                    ]
                    if candidate is not None
                ),
                None,
            )
        if value is not None:
            details.append((label, value))
    return details


def _selected_kpi_details(
    item: Dict[str, Any],
    records: List[Dict[str, Any]],
) -> List[tuple[str, Any]]:
    name = _item_name(item, "")
    if "hbu" in name.casefold():
        option_details = _hbu_option_details(
            records,
            top_ranked="top-ranked" in name.casefold(),
        )
        if option_details:
            return option_details

    row_details = _dashboard_kpi_details(item, records)
    if any(
        label in {
            "Actual", "Forecast", "Current", "Current Count", "Statistic",
            "Latest Actual", "Latest Forecast", "Variance",
            "Current Launch Count", "Current Dashboard Observation",
        }
        for label, _ in row_details
    ):
        return row_details
    details = _value_details(item) or row_details
    if "competitor" in name.casefold() or "launch" in name.casefold():
        return [
            (
                "Current Launch Count"
                if label in {"Value", "Statistic", "Current"}
                else label,
                value,
            )
            for label, value in details
        ]
    return details


def _hbu_option_details(
    records: List[Dict[str, Any]],
    *,
    top_ranked: bool,
) -> List[tuple[str, Any]]:
    option_rows = [
        row for row in records
        if any(row.get(key) not in (None, "") for key in ("option_id", "option_code", "candidate_id"))
        and any(row.get(key) not in (None, "") for key in ("weighted_score", "weighted_score_value"))
    ]
    if not option_rows:
        return []
    leading = next(
        (
            row for row in option_rows
            if _text(
                row.get("rank") or row.get("option_rank") or row.get("ranking")
            ).lstrip("#").strip() == "1"
        ),
        option_rows[0],
    )
    option = next(
        leading[key]
        for key in ("option_id", "option_code", "candidate_id")
        if leading.get(key) not in (None, "")
    )
    score = next(
        leading[key]
        for key in ("weighted_score", "weighted_score_value")
        if leading.get(key) not in (None, "")
    )
    details = [("Leading Option", option), ("Weighted Score", score)]
    rank = next(
        (
            leading[key]
            for key in ("rank", "option_rank", "ranking")
            if leading.get(key) not in (None, "")
        ),
        None,
    )
    if rank is not None:
        rank_text = _text(rank)
        details.append(("Rank", rank_text if rank_text.startswith("#") else f"#{rank_text}"))
    elif top_ranked:
        details.append(("Rank", "#1"))
    return details


def _aging_bucket_observation(records: List[Dict[str, Any]]) -> str:
    bucket_keys = {
        "90+": "90+ day",
        "90plus": "90+ day",
        "over90": "90+ day",
        "overdue90": "90+ day",
        "61to90": "61–90 day",
    }
    for record in records:
        bucket_name = _first_value_for_keys(
            record,
            ("bucket", "age_bucket", "aging_bucket", "label", "name"),
        )
        if (
            bucket_name is not None
            and re.search(r"90\s*\+|over\s*90|90\s*days?", _text(bucket_name), re.IGNORECASE)
        ):
            value = _first_display_value(record)
            if value is not None:
                return f"The 90+ day bucket contains {_display_text(value)}."
        for key, value in record.items():
            normalized_key = _normalized(key).replace(" ", "")
            if normalized_key in bucket_keys and value not in (None, ""):
                return f"The {bucket_keys[normalized_key]} bucket contains {_display_text(value)}."
    for record in records:
        bucket = _row_name(record)
        if re.search(r"\b90\s*\+\b|\b90\s*days?\s*\+?\b", bucket, re.IGNORECASE):
            value = _first_display_value(record)
            if value:
                return f"The 90+ day bucket contains {_display_text(value)}."
    return ""


def _first_value_for_keys(
    item: Dict[str, Any],
    keys: tuple[str, ...],
) -> Any:
    return next(
        (item[key] for key in keys if item.get(key) not in (None, "")),
        None,
    )


def _first_display_value(item: Dict[str, Any]) -> Any:
    for key in _KPI_VALUE_KEYS:
        value = item.get(key)
        if value not in (None, "") and _text(value):
            return value
    return None


def _supporting_kpi_reason(
    item: Dict[str, Any],
    records: List[Dict[str, Any]],
) -> str:
    reason = (
        item.get("why_it_matters")
        or item.get("business_relevance")
        or item.get("reasoning")
        or item.get("evidence")
    )
    if isinstance(reason, list):
        reason = next((value for value in reason if _text(value)), "")
    if reason:
        return _display_text(reason)
    name = _item_name(item, "This indicator").casefold()
    if "aging" in name or "payable" in name:
        bucket_observation = _aging_bucket_observation(records)
        if bucket_observation:
            return (
                f"{bucket_observation} This signals overdue supplier obligations, "
                "working-capital pressure, and elevated payment risk."
            )
        return (
            "The aging profile highlights overdue supplier obligations; concentration "
            "in older buckets signals working-capital pressure and elevated payment risk."
        )
    if "handover" in name or "near completion" in name:
        return (
            "Tracks projects approaching customer handover, helping leadership identify "
            "schedule slippage before it delays occupancy, revenue recognition, or collections."
        )
    if "cash" in name or "liquidity" in name:
        return (
            "Compares near-term cash generation with planned obligations, highlighting "
            "funding gaps early enough to protect payment capacity."
        )
    if "hbu" in name or "option" in name or "weighted score" in name:
        return (
            "Compares development feasibility and relative investment returns, supporting "
            "capital allocation toward the strongest viable opportunities."
        )
    if "competitor" in name or "launch" in name or "market" in name:
        return (
            "Tracks competitor activity and market positioning, helping leadership respond "
            "to changes in supply, pricing, and customer demand."
        )
    if "revenue" in name or "sales" in name or "conversion" in name:
        return (
            "Shows whether commercial performance is on track and helps identify emerging "
            "revenue or customer-conversion pressure."
        )
    if "cost" in name or "budget" in name or "variance" in name:
        return (
            "Highlights cost movement against plan so that emerging budget pressure can be "
            "addressed before it constrains delivery or returns."
        )
    return (
        f"{_item_name(item, 'This indicator')} provides a business-specific view of "
        "performance that helps leadership validate the primary KPI and target follow-up."
    )


def _render_kpi(
    item: Dict[str, Any],
    records: List[Dict[str, Any]],
    *,
    supporting: bool = False,
) -> List[str]:
    name = _item_name(item, "Business indicator")
    details = _selected_kpi_details(item, records)
    if not details:
        details = [("Value", "Value not available from dashboard metadata")]
    lines = [f"**{name}**"]
    lines.extend(
        f"- {label}: {_display_text(value)}"
        for label, value in details
    )
    if supporting:
        lines.append(f"- Why it matters: {_supporting_kpi_reason(item, records)}")
    return lines


def _action_details(action: Dict[str, Any]) -> str:
    return _display_text(
        action.get("action")
        or action.get("description")
        or action.get("details")
    )


def _render_risk(item: Dict[str, Any]) -> List[str]:
    lines = [f"**{_item_name(item, 'Business risk')}**"]
    for label, key in (
        ("Severity", "severity"),
        ("Impact", "business_impact"),
        ("Reason", "reason"),
    ):
        value = _display_text(item.get(key))
        if value:
            lines.append(f"- {label}: {value}")
    return lines


def _render_actions(actions: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for action in actions:
        title = _item_name(action, "Recommended action")
        detail = _display_text(
            action.get("expected_outcome")
            or action.get("business_benefit")
            or action.get("rationale")
        )
        lines.append(f"- **{title}**" + (f": {detail}" if detail else ""))
    return lines


def _tokens(value: Any) -> Set[str]:
    return {
        token.casefold()
        for token in re.findall(r"[a-zA-Z0-9]+", _text(value))
        if len(token) > 3 and token.casefold() not in _IRRELEVANT_WORDS
    }


def _is_relevant(text: Any, anchors: Set[str]) -> bool:
    return bool(_tokens(text).intersection(anchors))


def _relevant_root_cause(item: Dict[str, Any], anchors: Set[str]) -> Dict[str, Any]:
    result = {
        key: item[key]
        for key in ("root_cause", "cause", "confidence")
        if item.get(key) is not None
    }
    evidence = item.get("evidence")
    if isinstance(evidence, list):
        result["evidence"] = [
            value for value in evidence[:3] if _is_relevant(value, anchors)
        ]
    mitigation = item.get("recommended_mitigation") or item.get("mitigation")
    if mitigation:
        result["mitigation"] = mitigation
    return result


def _root_cause_matches(item: Dict[str, Any], anchors: Set[str]) -> bool:
    cause = item.get("root_cause") or item.get("cause")
    evidence = item.get("evidence")
    return _is_relevant(cause, anchors) or (
        isinstance(evidence, list)
        and any(_is_relevant(value, anchors) for value in evidence)
    )


def _dashboard_context(state: Dict[str, Any]) -> Dict[str, Any]:
    context = state.get("dashboard_context")
    context = context if isinstance(context, dict) else {}
    semantics = state.get("dashboard_semantics")
    if not isinstance(semantics, dict):
        semantics = context.get("dashboard_semantics")
    semantics = semantics if isinstance(semantics, dict) else {}

    return {
        "title": _display_text(
            context.get("title")
            or semantics.get("dashboard_name")
            or semantics.get("dashboard_title")
            or semantics.get("title")
        ),
    }


def _narrative_scenario(state: Dict[str, Any], query: str) -> tuple[str, str]:
    scenario = state.get("scenario")
    scenario = scenario if isinstance(scenario, dict) else {}
    description = _display_text(
        scenario.get("description")
        or scenario.get("change_description")
        or scenario.get("change_type")
    )
    normalized_query = _normalized(query)
    if normalized_query and _normalized(description) == normalized_query:
        description = ""
    entity = _display_text(
        state.get("primary_business_entity") or scenario.get("target_entity")
    )
    return description, entity


def _executive_summary(
    scenario_description: str,
    entity: str,
    primary_kpi: Dict[str, Any] | None,
    kpi_details: List[tuple[str, Any]],
    risk: Dict[str, Any] | None,
    business_impact: str,
    recommended_action: str,
    expected_outcome: str,
    supporting_kpis: List[Dict[str, Any]],
    dashboard_records: List[Dict[str, Any]],
) -> str:
    kpi_name = _item_name(primary_kpi, "business performance") if primary_kpi else "business performance"
    if scenario_description:
        changed = _sentence(scenario_description)
    elif entity:
        changed = _sentence(
            f"Current business conditions at {entity} require leadership attention"
        )
    elif kpi_details:
        changed = _sentence(
            f"The latest dashboard observation for {kpi_name} is {_display_text(kpi_details[0][1])}"
        )
    else:
        changed = _sentence(f"Leadership is reviewing {kpi_name}")

    evidence = "; ".join(
        f"{label.lower()} {_display_text(value)}"
        for label, value in kpi_details[:3]
        if label not in {
            "Leading Option",
            "Project",
            "Location",
            "Target Handover",
            "Status",
        }
    )
    if not evidence and kpi_details:
        evidence = ", ".join(
            f"{label.lower()} {_display_text(value)}"
            for label, value in kpi_details[:3]
        )
    why_parts = []
    if business_impact:
        why_parts.append(_sentence(f"This matters because {_lower_first(business_impact).rstrip('.!?')}"))
    if primary_kpi:
        indicator_sentence = f"The most important indicator is {kpi_name}"
        if evidence:
            indicator_sentence += f", with {evidence}"
        if entity and entity.casefold() not in indicator_sentence.casefold():
            indicator_sentence += f" informing the outlook for {entity}"
        why_parts.append(_sentence(indicator_sentence))
    elif evidence:
        why_parts.append(_sentence(f"Dashboard evidence shows {evidence}"))

    risk_name = _item_name(risk, "business continuity") if risk else "business continuity"
    risk_sentence = _sentence(f"The greatest business risk is {risk_name}")
    detail_labels = dict(kpi_details)
    project = detail_labels.get("Project")
    if project:
        project_context = f"Project observations identify {_display_text(project)}"
        if detail_labels.get("Location"):
            project_context += f" in {_display_text(detail_labels['Location'])}"
        if detail_labels.get("Target Handover"):
            project_context += (
                f", with target handover on {_display_text(detail_labels['Target Handover'])}"
            )
        if detail_labels.get("Status"):
            project_context += f" and status {_display_text(detail_labels['Status'])}"
        why_parts.append(_sentence(project_context))
    for supporting in supporting_kpis[:2]:
        supporting_name = _item_name(supporting, "business indicator")
        supporting_reason = _supporting_kpi_reason(supporting, dashboard_records)
        why_parts.append(
            _sentence(f"{supporting_name} also matters because {_lower_first(supporting_reason)}")
        )
    if recommended_action:
        action_sentence = _sentence(
            f"Leadership should {recommended_action[0].lower() + recommended_action[1:]}"
        )
        if expected_outcome:
            action_sentence = _sentence(
                f"{action_sentence.rstrip('.')} to help {_lower_first(expected_outcome).rstrip('.!?')}"
            )
    else:
        action_sentence = _sentence(
            f"Leadership should set clear accountability for {kpi_name} and monitor progress"
        )
    narrative = " ".join([changed, *why_parts, risk_sentence, action_sentence])
    return _limit_words(narrative, 120)


def _executive_conclusion(
    business_impact: str,
    risk: Dict[str, Any] | None,
    recommended_action: str,
    primary_kpi: Dict[str, Any] | None,
) -> str:
    outcome = (
        _sentence(f"Without intervention, {_lower_first(business_impact).rstrip('.!?')}")
        if business_impact
        else _sentence(
            f"Maintaining focus on "
            f"{_item_name(primary_kpi, 'business performance') if primary_kpi else 'business performance'} "
            "will support timely business decisions"
        )
    )
    if risk:
        risk_sentence = f"The principal business risk remains {_item_name(risk, 'business continuity')}"
        risk_reason = _display_text(risk.get("reason"))
        if risk_reason:
            risk_sentence += f", supported by {_lower_first(risk_reason)}"
        risk_sentence = _sentence(risk_sentence)
    else:
        risk_sentence = _sentence(
            "The principal business risk should be monitored against the available dashboard evidence"
        )
    action_sentence = (
        _sentence(f"Leadership should {recommended_action[0].lower() + recommended_action[1:]}")
        if recommended_action
        else _sentence(
            f"Leadership should confirm an accountable response and monitor "
            f"{_item_name(primary_kpi, 'business performance') if primary_kpi else 'business performance'} regularly"
        )
    )
    return " ".join((outcome, risk_sentence, action_sentence))


def _limit_words(value: str, maximum: int) -> str:
    words = value.split()
    if len(words) <= maximum:
        return value
    truncated = " ".join(words[:maximum]).rstrip(" ,;:")
    return truncated if truncated.endswith((".", "!", "?")) else f"{truncated}."


class ReportService:
    """Render selected scenario decisions without recalculating business conclusions."""

    async def generate_report(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = _display_query(state.get("query"))
        primary_kpi = state.get("primary_kpi")
        primary_kpi = primary_kpi if isinstance(primary_kpi, dict) else None
        supporting_kpis = _decision_items(state.get("supporting_kpis"))
        primary_risk = state.get("primary_risk")
        primary_risk = primary_risk if isinstance(primary_risk, dict) else None
        secondary_risk = state.get("secondary_risk")
        secondary_risk = secondary_risk if isinstance(secondary_risk, dict) else None
        selected_actions = _decision_items(state.get("selected_actions"))
        dashboard = _dashboard_context(state)
        dashboard_records = _dashboard_records(state)
        scenario_description, primary_entity = _narrative_scenario(state, query)

        anchors = _tokens(query)
        anchors.update(_tokens(state.get("scenario")))
        for item in (
            ([primary_kpi] if primary_kpi else [])
            + supporting_kpis
            + ([primary_risk] if primary_risk else [])
            + ([secondary_risk] if secondary_risk else [])
            + selected_actions
        ):
            anchors.update(_tokens(_item_name(item, "")))

        impact = state.get("impact_result")
        impact = impact if isinstance(impact, dict) else {}
        causal_analysis = impact.get("causal_analysis")
        causal_analysis = causal_analysis if isinstance(causal_analysis, dict) else {}
        causal_path = _display_text(causal_analysis.get("primary_impact_path"))
        if causal_path and not _is_relevant(causal_path, anchors):
            causal_path = ""

        root_causes = impact.get("root_cause_analysis")
        root_causes = root_causes if isinstance(root_causes, list) else []
        relevant_root_causes = [
            _relevant_root_cause(item, anchors)
            for item in root_causes
            if isinstance(item, dict) and _root_cause_matches(item, anchors)
        ][:5]

        primary_kpi_name = (
            _item_name(primary_kpi, "Business performance") if primary_kpi else ""
        )
        first_action = selected_actions[0] if selected_actions else {}
        action_name = _item_name(first_action, "Recommended action") if first_action else ""
        action_detail = _action_details(first_action) if first_action else ""
        decision_statement = (
            action_detail
            or action_name
            or "Leadership should confirm the next business action."
        )
        conclusion_risk = primary_risk or secondary_risk
        business_impact = ""
        if conclusion_risk:
            business_impact = _display_text(
                conclusion_risk.get("business_impact") or conclusion_risk.get("reason")
            )
        if not business_impact and primary_kpi:
            business_impact = _display_text(
                primary_kpi.get("why_it_matters")
                or primary_kpi.get("business_relevance")
                or primary_kpi.get("reasoning")
            )

        expected_outcome = _display_text(
            first_action.get("expected_outcome")
            or first_action.get("business_benefit")
        )

        primary_details = (
            _selected_kpi_details(primary_kpi, dashboard_records)
            if primary_kpi
            else []
        )
        situation = (
            f"Leadership's decision focus is {primary_kpi_name}."
            if primary_kpi
            else "Leadership should address the material business implications."
        )

        decision_required = {
            "situation": situation,
            "business_impact": business_impact or "No specific business impact was supplied.",
            "decision_required": decision_statement,
            "expected_outcome": expected_outcome or "No expected outcome was supplied.",
        }
        summary = _executive_summary(
            scenario_description,
            primary_entity,
            primary_kpi,
            primary_details,
            conclusion_risk,
            business_impact,
            action_detail or action_name,
            expected_outcome,
            supporting_kpis,
            dashboard_records,
        )

        markdown_lines = [
            "# Executive Scenario Report",
            "",
            query,
        ]
        if dashboard["title"]:
            markdown_lines.append(f"Dashboard: **{dashboard['title']}**")
        timestamp = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).strftime(
            "%Y-%m-%d %H:%M:%S IST"
        )
        markdown_lines.extend([
            f"Generated: {timestamp}",
            "",
            "## Executive Summary",
            summary,
            "",
            "## Executive Decision Required",
            f"**Decision Required:** {_display_text(decision_statement)}",
            "",
            "## Primary KPI",
        ])
        if primary_kpi:
            markdown_lines.extend(_render_kpi(primary_kpi, dashboard_records))
        else:
            markdown_lines.append("No primary business indicator was provided.")

        markdown_lines.extend(["", "## Supporting KPIs"])
        if supporting_kpis:
            for item in supporting_kpis:
                markdown_lines.extend(_render_kpi(item, dashboard_records, supporting=True))
        else:
            markdown_lines.append("No supporting business indicators were provided.")

        markdown_lines.extend(["", "## Primary Risk"])
        markdown_lines.extend(
            _render_risk(primary_risk) if primary_risk else ["No primary business risk was provided."]
        )
        markdown_lines.extend(["", "## Secondary Risk"])
        markdown_lines.extend(
            _render_risk(secondary_risk)
            if secondary_risk
            else ["No secondary business risk was provided."]
        )

        markdown_lines.extend(["", "## Recommended Actions"])
        markdown_lines.extend(
            _render_actions(selected_actions)
            if selected_actions
            else ["No recommended actions are available."]
        )

        if relevant_root_causes:
            markdown_lines.extend(["", "## Root Cause Analysis"])
            for item in relevant_root_causes:
                cause = _display_text(item.get("root_cause") or item.get("cause"))
                if cause:
                    markdown_lines.append(f"- **{cause}**")
                evidence = item.get("evidence")
                if isinstance(evidence, list):
                    markdown_lines.extend(
                        f"  - Evidence: {_display_text(value)}"
                        for value in evidence[:3]
                    )
                mitigation = _display_text(item.get("mitigation"))
                if mitigation:
                    markdown_lines.append(f"  - Mitigation: {mitigation}")
                if item.get("confidence") is not None:
                    markdown_lines.append(f"  - Confidence: {item['confidence']}")

        if causal_path:
            markdown_lines.extend([
                "",
                "## Causal Impact Analysis",
                f"**Business impact path:** {causal_path}",
                ])

        conclusion_text = _executive_conclusion(
            business_impact,
            conclusion_risk,
            action_detail or action_name,
            primary_kpi,
        )
        markdown_lines.extend([
            "",
            "## Executive Conclusion",
            conclusion_text,
        ])

        return {
            "report_id": f"REP-{uuid.uuid4().hex[:8].upper()}",
            "title": "Executive Scenario Report",
            "generated_at": timestamp,
            "business_query": query,
            "dashboard_context": dashboard,
            "executive_summary": summary,
            "executive_decision_required": decision_required,
            "primary_kpi": primary_kpi,
            "supporting_kpis": supporting_kpis,
            "primary_risk": primary_risk,
            "secondary_risk": secondary_risk,
            "selected_actions": selected_actions,
            "root_cause_analysis": relevant_root_causes,
            "causal_analysis": (
                {"primary_impact_path": causal_path}
                if causal_path
                else {}
            ),
            "financial_impact": None,
            "executive_conclusion": conclusion_text,
            "markdown_report": "\n".join(markdown_lines),
        }
