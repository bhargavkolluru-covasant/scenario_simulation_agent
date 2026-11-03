import datetime
import re
import uuid
from typing import Any, Dict, List, Set
from zoneinfo import ZoneInfo


_IRRELEVANT_WORDS = {
    "about", "after", "against", "along", "also", "and", "are", "because",
    "business", "could", "from", "have", "into", "more", "only", "over",
    "risk", "scenario", "selected", "should", "that", "their", "there",
    "these", "this", "through", "under", "using", "what", "when", "where",
    "which", "while", "with", "would",
}


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _display_query(value: Any) -> str:
    words = _text(value, "Scenario assessment").split()
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
    return _text(
        item.get("name")
        or item.get("kpi_name")
        or item.get("risk_name")
        or item.get("title")
        or item.get("action_title")
        or item.get("action"),
        default,
    )


def _render_kpi(item: Dict[str, Any]) -> str:
    name = _item_name(item, "Selected KPI")
    value = item.get("value")
    if value is None or not _text(value):
        value = item.get("kpi_value")
    if value is None or not _text(value):
        value = "Value not available from dashboard metadata"
    detail = f"**{name}**"
    return f"{detail}: {_text(value)}"


def _action_details(action: Dict[str, Any]) -> str:
    return _text(
        action.get("action")
        or action.get("description")
        or action.get("details")
    )


def _render_risk(item: Dict[str, Any]) -> List[str]:
    lines = [f"**{_item_name(item, 'Selected risk')}**"]
    for label, key in (
        ("Severity", "severity"),
        ("Impact", "business_impact"),
        ("Reason", "reason"),
    ):
        value = _text(item.get(key))
        if value:
            lines.append(f"- {label}: {value}")
    return lines


def _render_actions(actions: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for action in actions:
        title = _item_name(action, "Selected action")
        detail = _text(
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

    dashboard_kpis = state.get("selected_dashboard_kpi_names")
    dashboard_kpis = list(dashboard_kpis) if isinstance(dashboard_kpis, list) else []
    widget_titles = semantics.get("widget_titles")
    if isinstance(widget_titles, list):
        dashboard_kpis.extend(widget_titles)
    widget_kpis = state.get("dashboard_widget_kpis", [])
    if isinstance(widget_kpis, list):
        dashboard_kpis.extend(
            _item_name(item, "")
            for item in widget_kpis
            if isinstance(item, dict)
        )

    return {
        "title": _text(
            context.get("title")
            or semantics.get("dashboard_name")
            or semantics.get("dashboard_title")
            or semantics.get("title")
        ),
        "kpis": list(dict.fromkeys(
            _text(name) for name in dashboard_kpis if _text(name)
        )),
    }


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
        scenario = state.get("scenario")
        scenario = scenario if isinstance(scenario, dict) else {}
        scenario_description = _text(
            scenario.get("description")
            or scenario.get("change_description")
            or scenario.get("change_type")
        )
        normalized_query = " ".join(re.findall(r"[a-z0-9]+", query.casefold()))
        normalized_scenario = " ".join(
            re.findall(r"[a-z0-9]+", scenario_description.casefold())
        )
        if normalized_query and (
            normalized_query in normalized_scenario
            or normalized_scenario in normalized_query
        ):
            scenario_description = ""

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
        causal_path = _text(causal_analysis.get("primary_impact_path"))
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
            _item_name(primary_kpi, "Selected KPI") if primary_kpi else ""
        )
        primary_risk_name = (
            _item_name(primary_risk, "Selected risk") if primary_risk else ""
        )
        first_action = selected_actions[0] if selected_actions else {}
        action_name = _item_name(first_action, "Selected action") if first_action else ""
        action_detail = _action_details(first_action) if first_action else ""
        business_impact = ""
        if primary_risk:
            business_impact = _text(
                primary_risk.get("business_impact") or primary_risk.get("reason")
            )
        if not business_impact and primary_kpi:
            business_impact = _text(
                primary_kpi.get("why_it_matters")
                or primary_kpi.get("business_relevance")
                or primary_kpi.get("reasoning")
            )

        situation = (
            f"{scenario_description.rstrip('.')} is being assessed through "
            f"{primary_kpi_name}."
            if scenario_description and primary_kpi
            else (
                f"The selected dashboard indicator is {primary_kpi_name}."
                if primary_kpi
                else (
                    f"{scenario_description.rstrip('.')} is being assessed."
                    if scenario_description
                    else "The scenario is being assessed against the selected business decisions."
                )
            )
        )
        expected_outcome = _text(
            first_action.get("expected_outcome")
            or first_action.get("business_benefit")
        )
        if not expected_outcome:
            expected_outcome = action_detail
        if not expected_outcome and primary_kpi:
            expected_outcome = (
                f"Maintain focus on {primary_kpi_name} and the selected risk."
                if primary_risk
                else f"Maintain focus on {primary_kpi_name}."
            )

        summary_parts = [situation]
        if business_impact:
            summary_parts.append(business_impact.rstrip(".") + ".")
        elif primary_risk:
            summary_parts.append(
                f"The principal risk to manage is **{primary_risk_name}**."
            )
        if action_name:
            summary_parts.append(f"Leadership should {action_name[0].lower() + action_name[1:]}.")
        summary = " ".join(summary_parts)

        decision_required = {
            "situation": situation,
            "business_impact": business_impact or "No specific business impact was supplied.",
            "decision_required": (
                f"{action_name}: {action_detail}".rstrip(": ")
                if action_name and action_detail
                else action_name or "No action has been selected."
            ),
            "expected_outcome": expected_outcome or "No expected outcome was supplied.",
        }

        dashboard_kpis = [
            name for name in dashboard["kpis"]
            if name.casefold() not in {
                name.casefold()
                for name in (
                    [primary_kpi_name] if primary_kpi_name else []
                ) + [
                    _item_name(item, "") for item in supporting_kpis
                ]
            }
        ]

        markdown_lines = [
            "# Executive Scenario Report",
            "",
            query,
        ]
        if dashboard["title"]:
            markdown_lines.append(f"Dashboard: **{dashboard['title']}**")
        if dashboard_kpis:
            markdown_lines.append(
                "Dashboard KPIs: " + ", ".join(dashboard_kpis)
            )
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
            f"**Situation:** {decision_required['situation']}",
            f"**Business Impact:** {decision_required['business_impact']}",
            f"**Decision Required:** {decision_required['decision_required']}",
            f"**Expected Outcome:** {decision_required['expected_outcome']}",
            "",
            "## Primary KPI",
        ])
        if primary_kpi:
            markdown_lines.append(_render_kpi(primary_kpi))
        else:
            markdown_lines.append("No primary KPI was selected.")

        markdown_lines.extend(["", "## Supporting KPIs"])
        if supporting_kpis:
            markdown_lines.extend(f"- {_render_kpi(item)}" for item in supporting_kpis)
        else:
            markdown_lines.append("No supporting KPIs were selected.")

        markdown_lines.extend(["", "## Primary Risk"])
        markdown_lines.extend(
            _render_risk(primary_risk) if primary_risk else ["No primary risk was selected."]
        )
        markdown_lines.extend(["", "## Secondary Risk"])
        markdown_lines.extend(
            _render_risk(secondary_risk)
            if secondary_risk
            else ["No secondary risk was selected."]
        )

        markdown_lines.extend(["", "## Recommended Actions"])
        markdown_lines.extend(
            _render_actions(selected_actions)
            if selected_actions
            else ["No actions were selected."]
        )

        if relevant_root_causes:
            markdown_lines.extend(["", "## Root Cause Analysis"])
            for item in relevant_root_causes:
                cause = _text(item.get("root_cause") or item.get("cause"))
                if cause:
                    markdown_lines.append(f"- **{cause}**")
                evidence = item.get("evidence")
                if isinstance(evidence, list):
                    markdown_lines.extend(
                        f"  - Evidence: {value}"
                        for value in evidence[:3]
                    )
                mitigation = _text(item.get("mitigation"))
                if mitigation:
                    markdown_lines.append(f"  - Mitigation: {mitigation}")
                if item.get("confidence") is not None:
                    markdown_lines.append(f"  - Confidence: {item['confidence']}")

        if causal_path:
            markdown_lines.extend([
                "",
                "## Causal Impact Analysis",
                f"**Selected KPI impact path:** {causal_path}",
            ])

        conclusion_parts = []
        if primary_kpi:
            conclusion_parts.append(f"Track **{primary_kpi_name}**.")
        if primary_risk:
            conclusion_parts.append(f"Manage **{primary_risk_name}**.")
        if action_name:
            conclusion_parts.append(f"Proceed with **{action_name}**.")
        if not conclusion_parts:
            conclusion_parts.append("No selected decisions are available.")
        markdown_lines.extend([
            "",
            "## Executive Conclusion",
            " ".join(conclusion_parts),
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
            "executive_conclusion": " ".join(conclusion_parts),
            "markdown_report": "\n".join(markdown_lines),
        }
