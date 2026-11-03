import re
from typing import Any, Dict, Iterable, List, Optional, Tuple
import logging 


logger = logging.getLogger(__name__)

DASHBOARD_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "LAND_FEASIBILITY": {
        "business_intent": "Maximize risk-adjusted return on development options while ensuring zoning, hurdle rate, and capital feasibility",
        "decision_type": "Capital Allocation & Feasibility Hurdle Evaluation",
        "relevant_data_domain": "Real Estate Feasibility, HBU Valuation, and Development Cost Accounting",
        "supported_scenario_types": [
            "Capital Reduction",
            "Commercial Unviability",
            "IRR Hurdle Rate Stress",
            "Zoning Approval Delay",
            "Development Cost Escalation",
            "GDV Value Decline",
            "Portfolio Prioritization",
        ],
        "kpi_groups": [
            "development feasibility",
            "investment returns",
            "development value and cost",
            "zoning and approvals",
            "portfolio ranking",
        ],
        "kpi_terms": [
            "hbu option",
            "highest and best use",
            "weighted score",
            "hbu score",
            "rank",
            "irr",
            "internal rate of return",
            "gdv",
            "gross development value",
            "development cost",
            "hurdle rate",
            "zoning confidence",
            "approved development option",
            "investment capital",
            "capital allocation",
            "feasibility",
        ],
        "risk_groups": [
            "Investment Viability Risk",
            "Capital Allocation Risk",
            "Portfolio Optimization Risk",
            "Development Feasibility Risk",
        ],
        "action_groups": [
            "Investment prioritization",
            "Feasibility model review",
            "Capital allocation optimization",
            "Development option comparison",
        ],
    },
    "MARKET_INTELLIGENCE": {
    "business_intent": "Monitor market demand, pricing dynamics, competitor activity, supply pressure, and sentiment trends",
    "decision_type": "Market Strategy & Demand Management",
    "relevant_data_domain": "Market Intelligence, Pricing Analytics & Competitive Monitoring",
    "supported_scenario_types": [
        "Price Decline",
        "Market Slowdown",
        "Supply Increase",
        "Sentiment Deterioration",
        "Competitor Expansion",
        "Demand Reduction",
    ],
    "kpi_groups": [
        "market pricing",
        "supply",
        "competitor activity",
        "sentiment",
        "market confidence",
    ],
    "kpi_terms": [
        "dld price psf",
        "price psf",
        "price trend",
        "reidin",
        "reidin index",
        "upcoming supply",
        "competitor launches",
        "news sentiment",
        "market sentiment",
        "market confidence",
        "sales velocity",
        "supply",
        "demand",
    ],
    "risk_groups": [
        "Market Oversupply Risk",
        "Demand Slowdown Risk",
        "Price Compression Risk",
        "Competitive Pressure Risk",
        "Market Confidence Risk",
    ],
    "action_groups": [
        "Pricing strategy",
        "Launch strategy",
        "Demand generation",
        "Inventory optimisation",
        "Market positioning",
    ],
},
    "PROJECT_DELIVERY": {
        "business_intent": "Ensure on-time, on-budget project delivery across critical milestones, EPC contractors, and handover schedules",
        "decision_type": "Schedule Recovery, Critical Path Acceleration & Contractor Governance",
        "relevant_data_domain": "EPC Project Controls, Construction Schedule & Contractor Performance",
        "supported_scenario_types": [
            "Project Delay",
            "Handover Slippage",
            "Milestone Variance",
            "Contractor Underperformance",
            "Budget Overrun",
            "Critical Path Disruption",
        ],
        "kpi_groups": ["project schedule", "delivery cost", "contractor performance"],
        "kpi_terms": [
            "project delay", "contract variance", "budget overrun",
            "schedule performance", "contractor performance", "handover",
            "construction risk", "milestone variance", "critical path",
            "project handover delay",
        ],
        "risk_groups": [
            "Project Delivery Risk",
            "Cost Escalation Risk",
            "Schedule Slippage Risk",
            "Resource Constraint Risk",
        ],
        "action_groups": ["Schedule recovery", "Resource reallocation", "Contractor performance"],
    },
    "FINANCE": {
        "business_intent": "Preserve working capital liquidity, control expenditure variance, and optimize cash flow timing",
        "decision_type": "Liquidity Management & Working Capital Allocation",
        "relevant_data_domain": "Corporate Treasury, Accounts Payable/Receivable, and Cash Flow Projections",
        "supported_scenario_types": [
            "Cash Flow Deficit",
            "Working Capital Squeeze",
            "Collections Delay",
            "Cost Inflation",
        ],
        "kpi_groups": ["cash flow", "liquidity", "revenue and margin", "collections"],
        "kpi_terms": [
            "cash flow", "cashflow", "liquidity", "revenue", "profit",
            "margin", "receivables", "collections", "debt", "working capital",
        ],
        "risk_groups": ["Liquidity Risk", "Revenue Risk", "Margin Risk"],
        "action_groups": ["Cash flow protection", "Collections acceleration", "Cost control"],
    },
    "PORTFOLIO": {
        "business_intent": "Optimize risk-adjusted returns and capital allocation across enterprise asset portfolios",
        "decision_type": "Portfolio Capital Allocation & Asset Divestment/Investment",
        "relevant_data_domain": "Asset Management, Portfolio Performance & Weighted Scoring",
        "supported_scenario_types": [
            "Capital Budget Cut",
            "Portfolio Rebalancing",
            "Asset Underperformance",
        ],
        "kpi_groups": ["portfolio ranking", "asset performance", "investment returns"],
        "kpi_terms": [
            "portfolio rank", "portfolio score", "asset performance",
            "investment return", "irr", "gdv", "weighted score",
            "capital allocation", "portfolio value",
        ],
        "risk_groups": [
            "Portfolio Optimization Risk",
            "Capital Allocation Risk",
            "Investment Viability Risk",
        ],
        "action_groups": ["Portfolio prioritization", "Capital allocation", "Asset optimization"],
    },
    "SALES": {
        "business_intent": "Accelerate sales velocity, maximize pipeline conversion, and protect commercial revenue generation",
        "decision_type": "Pipeline Prioritization & Commercial Revenue Protection",
        "relevant_data_domain": "Commercial CRM, Bookings, Conversion Funnel & Sales Pipeline",
        "supported_scenario_types": [
            "Revenue Decline",
            "Booking Cancellation",
            "Lead Conversion Drop",
            "Sales Cycle Lengthening",
        ],
        "kpi_groups": ["bookings", "conversion", "revenue", "channel performance"],
        "kpi_terms": [
            "bookings", "sales conversion", "revenue", "lead conversion",
            "channel performance", "pipeline conversion", "sales pipeline",
        ],
        "risk_groups": ["Revenue Risk", "Pipeline Risk", "Conversion Risk"],
        "action_groups": ["Pipeline prioritization", "Conversion improvement", "Channel optimization"],
    },
    "CUSTOMER": {
        "business_intent": "Retain key accounts, elevate customer lifetime value (LTV), and safeguard customer satisfaction (CSAT/NPS)",
        "decision_type": "Key Account Retention & Service Quality Remediation",
        "relevant_data_domain": "Customer Success, Retention, CSAT/NPS Surveys & Churn Analytics",
        "supported_scenario_types": [
            "Customer Churn",
            "CSAT Degradation",
            "NPS Reduction",
            "Service SLA Breach",
        ],
        "kpi_groups": ["customer satisfaction", "retention", "loyalty", "customer value"],
        "kpi_terms": [
            "csat", "customer satisfaction", "retention", "nps",
            "net promoter score", "customer churn", "customer lifetime value",
            "customer experience",
        ],
        "risk_groups": [
            "Customer Retention Risk",
            "Customer Experience Risk",
            "Customer Churn Risk",
        ],
        "action_groups": ["Customer recovery", "Retention improvement", "Service quality"],
    },
    "RISK": {
        "business_intent": "Identify, monitor, and mitigate enterprise and operational risk exposures",
        "decision_type": "Enterprise Risk Mitigation & Crisis Management",
        "relevant_data_domain": "Enterprise Risk Register & Incident Response",
        "supported_scenario_types": [
            "Enterprise Risk Escalation",
            "Operational Failure",
            "Business Interruption",
        ],
        "kpi_groups": ["risk exposure", "risk likelihood", "control effectiveness"],
        "kpi_terms": ["risk exposure", "risk likelihood", "risk rating", "control effectiveness"],
        "risk_groups": ["Operational Risk", "Financial Risk", "Control Risk"],
        "action_groups": ["Risk mitigation", "Control improvement", "Exposure monitoring"],
    },
    "COMPLIANCE": {
        "business_intent": "Maintain regulatory adherence, enforce governance standards, and mitigate audit findings",
        "decision_type": "Regulatory Remediation & Compliance Oversight",
        "relevant_data_domain": "Enterprise Governance, Regulatory Compliance & Internal Audit",
        "supported_scenario_types": [
            "Regulatory Violation",
            "Audit Control Deficiency",
            "Sanctions Exposure",
        ],
        "kpi_groups": ["regulatory compliance", "audit", "policy controls"],
        "kpi_terms": [
            "regulatory", "compliance finding", "audit finding",
            "policy exception", "control breach", "violation",
        ],
        "risk_groups": ["Regulatory Risk", "Audit Risk", "Control Risk"],
        "action_groups": ["Regulatory remediation", "Audit response", "Control improvement"],
    },
    "PROCUREMENT": {
        "business_intent": "Ensure vendor reliability, contract compliance, and sourcing cost efficiency",
        "decision_type": "Supplier Performance Remediation & Sourcing Optimization",
        "relevant_data_domain": "Procurement, Vendor Management & Purchase Order Execution",
        "supported_scenario_types": [
            "Supplier Disruption",
            "Vendor Insolvency",
            "Contract Variance",
        ],
        "kpi_groups": ["supplier performance", "contract management", "sourcing"],
        "kpi_terms": [
            "supplier performance", "vendor performance", "contract variance",
            "procurement cost", "sourcing", "purchase order",
        ],
        "risk_groups": ["Supplier Performance Risk", "Contract Risk", "Sourcing Risk"],
        "action_groups": ["Supplier recovery", "Contract review", "Sourcing optimization"],
    },
    "OPERATIONS": {
        "business_intent": "Maintain high operational throughput, equipment availability, and capacity utilization",
        "decision_type": "Capacity Rebalancing & Operational Continuity",
        "relevant_data_domain": "Operational Operations, Supply Logistics & Asset Maintenance",
        "supported_scenario_types": [
            "Capacity Outage",
            "Downtime Surge",
            "Production Bottleneck",
        ],
        "kpi_groups": ["operational performance", "capacity", "service continuity"],
        "kpi_terms": [
            "operational performance", "throughput", "capacity",
            "productivity", "downtime", "service level", "quality",
        ],
        "risk_groups": ["Operational Performance Risk", "Capacity Risk", "Continuity Risk"],
        "action_groups": ["Capacity recovery", "Operational improvement", "Continuity planning"],
    },
}

_CATEGORY_SIGNALS: Dict[str, Tuple[str, ...]] = {
    "LAND_FEASIBILITY": (
        "land feasibility", "hbu", "highest and best use", "zoning confidence",
        "development option", "hurdle rate", "gdv", "development cost", "weighted score",
    ),
    "PROJECT_DELIVERY": (
        "project delivery", "project delay", "schedule performance",
        "contractor performance", "handover", "construction project",
    ),
    "FINANCE": ("finance dashboard", "cash flow", "liquidity", "receivables"),
    "PORTFOLIO": ("portfolio dashboard", "portfolio ranking", "asset portfolio"),
    "SALES": ("sales dashboard", "bookings", "lead conversion", "sales pipeline"),
    "CUSTOMER": ("customer dashboard", "csat", "customer satisfaction", "nps", "retention"),
    "RISK": ("risk dashboard", "risk exposure", "risk register"),
    "COMPLIANCE": ("compliance dashboard", "audit findings", "regulatory compliance"),
    "PROCUREMENT": ("procurement dashboard", "supplier performance", "vendor performance"),
    "OPERATIONS": ("operations dashboard", "operational performance", "throughput"),
    "MARKET_INTELLIGENCE": (
    "market & competitive intelligence",
    "market intelligence",
    "dld",
    "reidin",
    "price psf",
    "upcoming supply",
    "competitor launches",
    "market sentiment",
    "news sentiment",
    "sales velocity",
    "market confidence",
),
}
_LABEL_KEYS = {
    "title", "name", "label", "display_name", "dashboard_title", "section",
    "section_name", "widget_title", "kpi_name", "metric_name", "metric",
    "description",
}
_VALUE_KEYS = ("value", "current_value", "metric_value", "score", "amount", "count")
_IDENTITY_KEYS = (
    "option_id", "option_code", "development_option", "hbu_option",
    "option_name", "candidate_id", "candidate", "project_name", "name", "id",
)


def _normalized(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))

def _extract_dashboard_semantics(
    definition: Dict[str, Any],
    data: Dict[str, Any],
) -> Dict[str, Any]:

    dashboard_name = (
        definition.get("name")
        or data.get("name")
        or ""
    )

    dashboard_description = (
        definition.get("description")
        or data.get("description")
        or ""
    )
    widgets = []

    raw_widgets = (
    definition.get("widgets")
    or data.get("widgets")
    or []
)

    for widget in raw_widgets:

        if not isinstance(widget, dict):
            continue

        widgets.append(
        {
            "title": widget.get(
                "title",
                "",
            ),
            "description": widget.get(
                "description",
                "",
            ),
            "widget_type": widget.get(
                "widget_type",
                "",
            ),
        }
    )

    widget_titles = [
        w["title"]
        for w in widgets
        if w["title"]
    ]

    all_text = " ".join(
        [
            dashboard_name,
            dashboard_description,
            *widget_titles,
        ]
    ).casefold()

    themes = []

    if any(
        k in all_text
        for k in (
            "competitor",
            "competition",
            "launch",
        )
    ):
        themes.append("competition")

    if any(
        k in all_text
        for k in (
            "sentiment",
            "news",
        )
    ):
        themes.append(
            "market_sentiment"
        )

    if any(
        k in all_text
        for k in (
            "price",
            "psf",
            "reidin",
        )
    ):
        themes.append("pricing")

    if any(
        k in all_text
        for k in (
            "supply",
            "units planned",
        )
    ):
        themes.append("supply")

    if any(
        k in all_text
        for k in (
            "booking",
            "sales",
            "conversion",
        )
    ):
        themes.append("sales")

    if any(
        k in all_text
        for k in (
            "irr",
            "gdv",
            "feasibility",
            "hbu",
        )
    ):
        themes.append(
            "investment_feasibility"
        )

    business_domain = (
        dashboard_name.split("]")
        [-1]
        .strip()
        if "]" in dashboard_name
        else dashboard_name
    )

    return {
        "business_domain":
            business_domain,
        "dashboard_name":
            dashboard_name,
        "dashboard_description":
            dashboard_description,
        "themes":
            list(dict.fromkeys(themes)),
        "widget_titles":
            widget_titles,
        "widget_count":
            len(widget_titles),
    }

def _semantic_theme_score(
    kpi_name: str,
    dashboard_themes: List[str],
    scenario_themes: List[str],
) -> float:
    candidate_tokens = set(_normalized(kpi_name).split())
    context_tokens = set(
        _normalized(
            " ".join(str(theme) for theme in dashboard_themes + scenario_themes)
        ).split()
    )
    return (
        len(candidate_tokens.intersection(context_tokens))
        / max(len(candidate_tokens), 1)
    )

def _nested_strings(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _nested_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _nested_strings(child)
    elif isinstance(value, (str, int, float)):
        yield str(value)


def _dashboard_labels(value: Any) -> List[str]:
    labels: List[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.casefold() in _LABEL_KEYS and isinstance(child, str):
                labels.append(child)
            labels.extend(_dashboard_labels(child))
    elif isinstance(value, list):
        for child in value:
            labels.extend(_dashboard_labels(child))
    return labels


def _metric_records(value: Any, terms: List[str]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    normalized_terms = [_normalized(term) for term in terms]

    def is_allowed(label: str) -> bool:
        normalized_label = _normalized(label)
        if not normalized_label:
            return False
        if not normalized_terms:
            return True
        return any(
            term in normalized_label
            for term in normalized_terms
            if len(term) > 2
        )

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            name = next(
                (
                    str(item[key])
                    for key in ("kpi_name", "metric_name", "name", "title", "label", "metric")
                    if item.get(key) not in (None, "")
                ),
                "",
            )
            metric_value = next(
                (item[key] for key in _VALUE_KEYS if item.get(key) not in (None, "")),
                None,
            )
            if name and metric_value is not None and is_allowed(name):
                records.append({
                    "name": name,
                    "value": metric_value,
                    "dashboard_evidence": True,
                })
            for key, child in item.items():
                if normalized_terms and is_allowed(key) and not isinstance(child, (dict, list)):
                    records.append({
                        "name": key.replace("_", " ").strip().title(),
                        "value": child,
                        "dashboard_evidence": True,
                    })
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    deduplicated: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for record in records:
        key = (_normalized(record["name"]), str(record["value"]))
        deduplicated[key] = record
    return list(deduplicated.values())


def resolve_dashboard_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 1: Dashboard Context Resolver
    Understand what business domain the current dashboard represents.
    Determines:
    - Dashboard Category
    - Business Intent
    - Decision Type
    - Relevant Data Domain
    - Supported Scenario Types
    """
    definition = state.get("dashboard_definition", {})
    data = state.get("dashboard_data", {})
    if not isinstance(definition, dict):
        definition = {}
    if not isinstance(data, dict):
        data = {}

    title = next(
        (
            str(source[key])
            for source in (definition, data)
            for key in ("title", "name", "dashboard_title", "display_name")
            if source.get(key)
        ),
        "",
    )
    labels = _dashboard_labels(definition) + _dashboard_labels(data)
    evidence = " ".join((title, *labels, *_nested_strings(data))).casefold()
    category_scores: Dict[str, int] = {}
    for category, signals in _CATEGORY_SIGNALS.items():
        score = sum(
            6 if title and signal in title.casefold()
            else 3 if any(signal in label.casefold() for label in labels)
            else 1
            for signal in signals
            if signal in evidence
        )
        category_scores[category] = score

    # Check if category already provided in state explicitly
    explicit_category = str(state.get("dashboard_category") or "").upper()
    if explicit_category in DASHBOARD_TAXONOMY:
        category = explicit_category
        has_dashboard_evidence = True
    else:
        category = max(category_scores, key=category_scores.get)
        has_dashboard_evidence = category_scores[category] > 0
        if not has_dashboard_evidence:
            category = "UNCLASSIFIED"

    dashboard_semantics = (
    _extract_dashboard_semantics(
        definition,
        data,
    )
)
    taxonomy = DASHBOARD_TAXONOMY.get(category, {})
    sections = [
        label for label in labels
        if "section" in label.casefold()
    ]
    widget_names = [
        label for label in labels
        if any(key in label.casefold() for key in ("widget", "chart", "table"))
    ]
    dashboard_metric_names = [
        record["name"]
        for record in _metric_records(data, [])
    ]
    widget_metric_names = [
        part.strip()
        for title in dashboard_semantics.get("widget_titles", [])
        if title
        for part in re.split(r"\s+(?:and|&)\s+|[,|/]", str(title), flags=re.IGNORECASE)
        if part.strip()
    ]
    kpi_names = list(dict.fromkeys(dashboard_metric_names + widget_metric_names))
    dashboard_kpi_terms = list(kpi_names)
    return {
        "title": title,
        "sections": sections,
        "widgets": widget_names,
        "kpi_names": kpi_names,
        "category": category,
        "category_resolved": has_dashboard_evidence,
        "category_evidence": [
            signal
            for signal in _CATEGORY_SIGNALS.get(category, ())
            if signal in evidence
        ],
        "business_intent": taxonomy.get("business_intent", ""),
        "decision_type": taxonomy.get("decision_type", ""),
        "relevant_data_domain": taxonomy.get("relevant_data_domain", ""),
        "supported_scenario_types": taxonomy.get("supported_scenario_types", []),
        "allowed_kpi_groups": taxonomy.get("kpi_groups", []),
        "allowed_kpi_terms": dashboard_kpi_terms,
        "allowed_risk_groups": taxonomy.get("risk_groups", []),
        "allowed_action_groups": taxonomy.get("action_groups", []),
        "category_scores": category_scores,
        "dashboard_semantics": dashboard_semantics,
    }


def select_relevant_kpis(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 3: Relevant KPI Selector
    Build a dashboard-scoped KPI pool and rank candidates using dashboard,
    scenario, entity, semantic, and confidence relevance.
    Returns 1 Primary KPI and 2 Supporting KPIs.
    """
    dashboard_context = state.get("dashboard_context", {})
    logger.info(
    "[KPI DEBUG] widget_kpis=%s",
    state.get(
        "dashboard_widget_kpis",
        []
    ),
)
    dashboard_semantics = (
    state.get("dashboard_semantics")
    or dashboard_context.get(
        "dashboard_semantics",
        {}
    )
)

    scenario_semantics = (
    state.get("scenario_semantics")
    or {}
)
    if not isinstance(dashboard_context, dict):
        dashboard_context = {}
    terms = dashboard_context.get("allowed_kpi_terms", [])
    if not isinstance(terms, list):
        terms = []

    dashboard_data = state.get("dashboard_data", {})
    rows = state.get("dashboard_rows", [])
    records = _metric_records(dashboard_data, terms)
    records.extend(_metric_records(rows, terms))

    unique_records: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for record in records:
        key = (_normalized(record["name"]), str(record["value"]))
        unique_records[key] = record

    scenario = state.get("scenario", {})
    query = str(state.get("query") or "")
    scenario_text = " ".join(
        [query]
        + [
            str(value)
            for value in scenario.values()
            if value not in (None, "")
        ]
        if isinstance(scenario, dict)
        else [query, str(scenario)]
    ).casefold()

    target_entity = str(
        state.get("primary_business_entity")
        or (scenario.get("target_entity") if isinstance(scenario, dict) else "")
        or ""
    )

    dashboard_category = str(
        dashboard_context.get("category") or state.get("dashboard_category") or ""
    ).upper()

    # Collect all candidates: dashboard records + incoming KPI insights
    kpi_insights = state.get("kpi_insights") or {}
    raw_kpis = []
    if isinstance(kpi_insights, dict):
        raw_kpis = kpi_insights.get("kpis") or []
    elif isinstance(kpi_insights, list):
        raw_kpis = kpi_insights

    all_candidates: List[Dict[str, Any]] = (
    list(unique_records.values())
    +
    state.get(
        "dashboard_widget_kpis",
        [],
    )
)
    logger.info(
    "[KPI DEBUG] total_candidates=%d",
    len(all_candidates),
)
    logger.info(
    "[KPI DEBUG] candidates=%s",
    [
        (
            c.get("name")
            or c.get("title")
        )
        for c in all_candidates[:20]
    ],
)
    for item in raw_kpis:
        if isinstance(item, dict):
            name = next(
                (item[key] for key in ("kpi_name", "metric_name", "name", "title", "label", "metric") if item.get(key)),
                "",
            )
            val = next((item[key] for key in _VALUE_KEYS if item.get(key) is not None), None)
            if name and val is not None:
                all_candidates.append(item)

    primary_kpi, supporting_kpis, scored_candidates = rank_kpis_by_formula(
        candidates=all_candidates,
        dashboard_category=dashboard_category,
        scenario_text=scenario_text,
        target_entity=target_entity,
        allowed_terms=terms,
        dashboard_themes=dashboard_semantics.get("themes", []),
        scenario_themes=scenario_semantics.get("themes", []),
        dashboard_kpi_names=(
            state.get("selected_dashboard_kpi_names")
            or dashboard_context.get("kpi_names", [])
        ),
        widget_titles=dashboard_semantics.get("widget_titles", []),
    )
    dashboard_names = dashboard_context.get("kpi_names", [])
    selected_names = list(dict.fromkeys(
        [str(record.get("name") or record.get("kpi_name")) for record in scored_candidates if record.get("name") or record.get("kpi_name")]
        + [str(name) for name in dashboard_names if name]
    ))

    return {
        "dashboard_kpi_records": scored_candidates,
        "selected_dashboard_kpi_names": selected_names,
        "allowed_kpi_terms": terms,
        "strict_dashboard_filter": bool(dashboard_context.get("category_resolved")),
        "primary_kpi": primary_kpi,
        "supporting_kpis": supporting_kpis,
    }


def rank_kpis_by_formula(
    candidates: List[Dict[str, Any]],
    dashboard_category: str,
    scenario_text: str,
    target_entity: str,
    allowed_terms: List[str],
    dashboard_themes: Optional[List[str]] = None,
    scenario_themes: Optional[List[str]] = None,
    dashboard_kpi_names: Optional[List[str]] = None,
    widget_titles: Optional[List[str]] = None,
)-> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Rank candidate KPIs using dashboard, scenario, entity, semantic, and confidence relevance.
    """
    normalized_scenario = _normalized(scenario_text)
    normalized_entity = _normalized(target_entity)
    dashboard_labels = {
        _normalized(label)
        for label in (dashboard_kpi_names or []) + (widget_titles or [])
        if _normalized(label)
    }

    scored_list = []
    seen_identities = set()

    for item in candidates:
        if not isinstance(item, dict):
            continue
        name = next(
            (str(item[key]) for key in ("kpi_name", "metric_name", "name", "title", "label", "metric") if item.get(key)),
            "",
        )
        if not name:
            continue
        value = next(
            (item[key] for key in _VALUE_KEYS if item.get(key) is not None),
            "",
        )
        identity = (_normalized(name), str(value))
        if identity in seen_identities:
            continue
        seen_identities.add(identity)

        semantic_score = (
            _semantic_theme_score(
                name,
                dashboard_themes or [],
                scenario_themes or [],
            )
        )

        norm_name = _normalized(name)
        name_tokens = set(norm_name.split())
        dashboard_rel = max(
            (
                len(name_tokens.intersection(label.split()))
                / max(len(name_tokens.union(label.split())), 1)
                for label in dashboard_labels
            ),
            default=0.0,
        )
        if norm_name in dashboard_labels:
            dashboard_rel = 1.0

        scenario_tokens = set(normalized_scenario.split())
        candidate_text = " ".join(
            str(value)
            for key, value in item.items()
            if not str(key).startswith("_") and value not in (None, "")
        )
        candidate_tokens = set(_normalized(candidate_text).split())
        scenario_rel = (
            len(candidate_tokens.intersection(scenario_tokens))
            / max(len(candidate_tokens), 1)
        )

        record_text = " ".join(str(v) for v in item.values()).casefold()
        if normalized_entity and normalized_entity in record_text:
            entity_rel = 1.0
        elif normalized_entity and any(tok in record_text for tok in normalized_entity.split()):
            entity_rel = 0.7
        else:
            entity_rel = 0.4

        # 4. Confidence (10%)
        raw_conf = next((item[key] for key in ("confidence_score", "confidence") if item.get(key) is not None), 0.7)
        try:
            conf = float(raw_conf)
            if conf > 1.0:
                conf /= 100.0
            conf = min(max(conf, 0.0), 1.0)
        except (ValueError, TypeError):
            conf = 0.7

        total_score = round(
            0.25 * dashboard_rel
            + 0.25 * scenario_rel
            + 0.20 * entity_rel
            + 0.20 * semantic_score
            + 0.10 * conf,
            4,
        )

        item_copy = dict(item)
        item_copy["name"] = name
        item_copy["value"] = value
        item_copy["_scoring"] = {
            "dashboard_relevance": dashboard_rel,
            "scenario_relevance": scenario_rel,
            "entity_relevance": entity_rel,
            "semantic_relevance": semantic_score,
            "confidence": conf,
            "total_score": total_score,
        }
        scored_list.append(item_copy)

    # Sort descending by formula total_score
    scored_list.sort(key=lambda x: x["_scoring"]["total_score"], reverse=True)

    if not scored_list:
        return None, [], []

    # 1 Primary KPI, 2 Supporting KPIs
    p_candidate = scored_list[0]
    p_name = p_candidate["name"]
    p_val = p_candidate["value"]
    unit = p_candidate.get("kpi_unit") or p_candidate.get("unit") or ""
    display_val = f"{p_val}{unit}" if unit and unit not in str(p_val) else str(p_val)

    why_it_matters = str(
        p_candidate.get("reasoning")
        or p_candidate.get("explanation")
        or f"{p_name} is the highest-ranked dashboard indicator for this scenario."
    )
    business_relevance = f"Dashboard and scenario evidence make {p_name} relevant to this assessment."

    primary_kpi = {
        "name": p_name,
        "value": display_val,
        "raw_value": p_val,
        "unit": unit,
        "why_it_matters": why_it_matters,
        "business_relevance": business_relevance,
        "confidence": p_candidate["_scoring"]["confidence"],
        "confidence_score": p_candidate["_scoring"]["confidence"],
        "total_score": p_candidate["_scoring"]["total_score"],
    }

    supporting_kpis = []
    for s_candidate in scored_list[1:3]:
        s_name = s_candidate["name"]
        s_val = s_candidate["value"]
        s_unit = s_candidate.get("kpi_unit") or s_candidate.get("unit") or ""
        s_display = f"{s_val}{s_unit}" if s_unit and s_unit not in str(s_val) else str(s_val)
        s_evidence = str(
            s_candidate.get("reasoning")
            or s_candidate.get("explanation")
            or f"Provides essential quantitative cross-validation for {p_name}."
        )
        supporting_kpis.append({
            "name": s_name,
            "value": s_display,
            "raw_value": s_val,
            "unit": s_unit,
            "evidence": s_evidence,
            "confidence": s_candidate["_scoring"]["confidence"],
            "total_score": s_candidate["_scoring"]["total_score"],
        })

    return primary_kpi, supporting_kpis, scored_list


def kpi_is_dashboard_relevant(
    name: Any,
    allowed_terms: List[str],
    dashboard_kpi_names: List[str],
) -> bool:
    normalized_name = _normalized(name)
    if not normalized_name:
        return False
    normalized_names = {_normalized(item) for item in dashboard_kpi_names}
    if normalized_name in normalized_names:
        return True
    return any(
        _normalized(term) in normalized_name
        for term in allowed_terms
        if len(_normalized(term)) > 2
    )


def rank_development_options(rows: Any) -> List[Dict[str, Any]]:
    """
    Capital Allocation Rule:
    Generate:
    - Investment Ranking (Priority 1, 2, 3)
    - Recommended Options
    - Deferred Options
    - Clear feasibility rationale with Weighted Score, IRR, Hurdle Rate, GDV, Development Cost, Zoning Confidence.
    """
    if not isinstance(rows, list):
        return []
    candidates: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized = {_normalized(key): value for key, value in row.items()}
        label = next(
            (
                str(row[key])
                for key in _IDENTITY_KEYS
                if row.get(key) not in (None, "")
            ),
            "",
        )
        if not label or _normalized(label) in {
            "weighted score",
            "hbu score",
            "irr",
            "gdv",
            "development cost",
            "hurdle rate",
            "zoning confidence",
        }:
            continue
        values = {
            "weighted_score": _find_number(normalized, ("weighted score", "hbu score", "score")),
            "irr": _find_number(normalized, ("irr", "internal rate of return")),
            "gdv": _find_number(normalized, ("gdv", "gross development value")),
            "development_cost": _find_number(normalized, ("development cost", "total cost", "cost")),
            "hurdle_rate": _find_number(normalized, ("hurdle rate",)),
            "zoning_confidence": _find_number(normalized, ("zoning confidence",)),
        }
        if not any(value is not None for value in values.values()):
            continue
        candidates.append({"option": label, **values})

    candidates.sort(
        key=lambda item: (
            item["irr"] is None
            or item["hurdle_rate"] is None
            or item["irr"] >= item["hurdle_rate"],
            item["weighted_score"] is not None,
            item["weighted_score"] if item["weighted_score"] is not None else float("-inf"),
            item["irr"] if item["irr"] is not None else float("-inf"),
            item["zoning_confidence"] if item["zoning_confidence"] is not None else float("-inf"),
        ),
        reverse=True,
    )
    for index, item in enumerate(candidates[:3], start=1):
        rationale = []
        if item["weighted_score"] is not None:
            rationale.append(f"weighted score {item['weighted_score']:g}")
        if item["irr"] is not None and item["hurdle_rate"] is not None:
            meets_hurdle = item["irr"] >= item["hurdle_rate"]
            rationale.append(
                f"IRR {item['irr']:g}% remains above the {item['hurdle_rate']:g}% hurdle rate"
                if meets_hurdle
                else f"IRR {item['irr']:g}% falls below the {item['hurdle_rate']:g}% hurdle rate and requires deferral"
            )
        elif item["irr"] is not None:
            rationale.append(f"IRR {item['irr']:g}%")
        if item["gdv"] is not None:
            rationale.append(f"GDV AED {item['gdv']:g}M" if item['gdv'] < 1000 else f"GDV AED {item['gdv']:,.0f}")
        if item["development_cost"] is not None:
            rationale.append(f"Development Cost AED {item['development_cost']:g}M" if item['development_cost'] < 1000 else f"Development Cost AED {item['development_cost']:,.0f}")
        if item["zoning_confidence"] is not None:
            rationale.append(f"zoning confidence {item['zoning_confidence']:g}")

        item["priority"] = index
        item["candidate_category"] = (
            "Primary Candidate" if index == 1
            else "Secondary Candidate" if index == 2
            else "Deferred Candidate"
        )
        item["rationale"] = (
            "Highest " + ", ".join(rationale)
            if index == 1 and rationale
            else ", ".join(rationale) if rationale
            else "Highest remaining risk-adjusted value based on available feasibility evidence"
        )

    return candidates[:3]


def _find_number(values: Dict[str, Any], terms: Tuple[str, ...]) -> Any:
    for key, value in values.items():
        if any(term in key for term in terms):
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                match = re.search(r"(\d+(?:\.\d+)?)", value.replace(",", ""))
                if match:
                    return float(match.group(1))
    return None
