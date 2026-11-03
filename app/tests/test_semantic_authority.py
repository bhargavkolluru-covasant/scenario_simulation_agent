import copy

import pytest
from unittest.mock import AsyncMock

from app.clients.actions_client import ActionsClient
from app.clients.kpi_insights_client import KPIInsightsClient
from app.nodes.action_selector_node import action_selector_node
from app.nodes.actions_node import actions_node
from app.nodes.kpi_insights_node import kpi_insights_node
from app.nodes.recommendation_node import recommendation_node
from app.nodes.risk_selector_node import risk_selector_node
import app.nodes.semantic_reasoning_node as semantic_node_module
from app.services.action_selector_service import ActionSelectorService
from app.services.dashboard_intelligence_service import rank_kpis_by_formula
from app.services.report_service import ReportService
from app.services.risk_selector_service import RiskSelectorService


@pytest.mark.asyncio
async def test_report_renders_only_authoritative_decision_state():
    primary_kpi = {"name": "Competitor Launches", "value": 12}
    supporting_kpis = [{"name": "Avg News Sentiment", "value": -0.4}]
    primary_risk = {"name": "Market-Share Erosion", "severity": "HIGH"}
    secondary_risk = {"name": "Pricing Pressure", "severity": "MEDIUM"}
    selected_actions = [{"title": "Reassess pricing", "priority": "HIGH"}]
    state = {
        "query": "Competitor activity rises while sentiment turns negative",
        "dashboard_category": "MARKET_INTELLIGENCE",
        "dashboard_context": {
            "title": "Market Dashboard",
            "dashboard_semantics": {
                "widget_titles": [
                    "Competitor Launches",
                    "Avg News Sentiment",
                    "Upcoming Supply",
                ],
            },
        },
        "selected_dashboard_kpi_names": [
            "Competitor Launches",
            "Avg News Sentiment",
            "Upcoming Supply",
        ],
        "primary_kpi": primary_kpi,
        "supporting_kpis": supporting_kpis,
        "primary_risk": primary_risk,
        "secondary_risk": secondary_risk,
        "selected_actions": selected_actions,
        "kpi_insights": {"kpis": [{"name": "Legacy KPI", "value": 99}]},
        "actions": [{"title": "Legacy action"}],
        "recommendations": [{"action_title": "Legacy recommendation"}],
        "impact_result": {
            "dimensions": [{"dimension_name": "Operational Risk"}],
            "causal_analysis": {"scenario_category": "LAND_FEASIBILITY"},
            "root_cause_analysis": [
                {
                    "root_cause": "Competitor market-share erosion",
                    "evidence": [
                        "Competitor launches increased against market peers.",
                        "Inactive broker bookings are AED 50M.",
                    ],
                    "confidence": 0.8,
                },
                {
                    "root_cause": "Bypassed payments on blacklisted contracts",
                    "evidence": ["Payment exceptions increased."],
                },
            ],
            "financial_model": {
                "current_exposure": {
                    "items": [{
                        "name": "Inactive Broker Bookings",
                        "formatted_amount": "AED 50M",
                    }],
                },
            },
        },
        "include_full_state": True,
    }
    original = copy.deepcopy(state)

    report = await ReportService().generate_report(state)

    assert report["primary_kpi"] is primary_kpi
    assert report["supporting_kpis"] == supporting_kpis
    assert report["primary_risk"] is primary_risk
    assert report["secondary_risk"] is secondary_risk
    assert report["selected_actions"] == selected_actions
    assert "Legacy KPI" not in report["markdown_report"]
    assert "Legacy action" not in report["markdown_report"]
    assert "Operational Risk" not in report["markdown_report"]
    assert "Market Dashboard" in report["markdown_report"]
    assert "Upcoming Supply" not in report["markdown_report"]
    assert report["dashboard_context"] == {"title": "Market Dashboard"}
    assert "Inactive Broker Bookings" not in report["markdown_report"]
    assert "AED 50M" not in report["markdown_report"]
    assert "## Financial Impact" not in report["markdown_report"]
    assert "Competitor market-share erosion" in report["markdown_report"]
    assert "Inactive broker bookings" not in report["markdown_report"]
    assert "Bypassed payments" not in report["markdown_report"]
    assert report["root_cause_analysis"][0]["evidence"] == [
        "Competitor launches increased against market peers."
    ]
    assert state == original


@pytest.mark.asyncio
async def test_report_is_an_executive_brief_and_prints_query_once_with_kpi_value_fallback():
    query = "What happens if cashflow actual falls below forecast?"
    report = await ReportService().generate_report({
        "query": query,
        "scenario": {"description": query},
        "dashboard_context": {
            "title": "Finance Dashboard",
            "dashboard_semantics": {
                "widget_titles": ["Cashflow Actual vs Forecast", "AP Aging Buckets"],
            },
        },
        "primary_kpi": {
            "name": "Cashflow Actual vs Forecast",
            "value": " ",
        },
        "supporting_kpis": [{"name": "AP Aging Buckets", "value": None}],
        "primary_risk": {
            "name": "Liquidity Pressure",
            "business_impact": "Reduced cash availability may constrain scheduled payments.",
        },
        "selected_actions": [{
            "title": "Review near-term cash commitments",
            "action": "Rephase discretionary outflows against the updated forecast.",
            "expected_outcome": "Protect funding for committed payments.",
        }],
    })

    markdown = report["markdown_report"]
    assert markdown.count(query) == 1
    assert "**Decision Required:**" in markdown
    assert markdown.count("Value not available from dashboard metadata") == 2
    assert "Finance Dashboard" in markdown
    assert "AP Aging Buckets" in markdown
    assert "## Executive Conclusion" in markdown
    assert len(report["executive_conclusion"].split(". ")) <= 3
    assert query not in report["executive_decision_required"]["situation"]
    assert query not in report["executive_conclusion"]


@pytest.mark.asyncio
async def test_report_formats_hbu_values_and_keeps_decision_once():
    primary_kpi = {"name": "Top-Ranked HBU Options"}
    action_text = (
        "Allocate capital only to the highest-ranked HBU options and defer "
        "lower-ranked developments."
    )
    report = await ReportService().generate_report({
        "query": "Which options should receive investment capital?",
        "scenario": {"description": "Investment capital is reduced by 30%."},
        "dashboard_context": {"title": "Highest Benefit Unit Dashboard"},
        "dashboard_widget_kpis": [
            {"name": "Unrelated Dashboard KPI", "value": 99},
        ],
        "dashboard_rows": [
            {
                "option_id": "OPT-0003",
                "weighted_score": 11.29,
            },
            {
                "option_id": "OPT-0021",
                "weighted_score": 10.4,
            },
        ],
        "primary_kpi": primary_kpi,
        "supporting_kpis": [{"name": "AP Aging Buckets"}],
        "primary_risk": {
            "name": "Capital Allocation Risk",
            "business_impact": "Viable high-return projects may be delayed.",
        },
        "selected_actions": [{
            "title": "Highest Benefit Unit: prioritize investments",
            "action": action_text,
            "expected_outcome": "Preserve capital for the strongest opportunities.",
        }],
    })

    markdown = report["markdown_report"]
    decision_section = markdown.split("## Executive Decision Required\n", 1)[1]
    decision_section = decision_section.split("\n## ", 1)[0]
    assert decision_section.count(action_text) == 1
    assert "Leading Option: OPT-0003" in markdown
    assert "Weighted Score: 11.29" in markdown
    assert "Rank: #1" in markdown
    assert "Why it matters:" in markdown
    assert "aging profile highlights overdue supplier obligations" in markdown
    assert "Highest Benefit Unit" not in markdown
    assert "Highest and Best Use (HBU)" in markdown
    assert "Unrelated Dashboard KPI" not in markdown
    assert "Dashboard KPIs:" not in markdown
    assert markdown.count("Which options should receive investment capital?") == 1
    assert len(report["executive_summary"].split()) <= 100
    assert len(report["executive_conclusion"].split(". ")) <= 3
    assert report["primary_kpi"] is primary_kpi


@pytest.mark.asyncio
async def test_report_uses_dashboard_finance_and_market_values():
    report = await ReportService().generate_report({
        "dashboard_category": "FINANCE",
        "dashboard_rows": [
            {
                "metric_name": "Cashflow Actual vs Forecast",
                "actual_value": "AED 8M",
                "forecast_value": "AED 10M",
            },
            {
                "statistic_name": "Competitor Launches by Detection Source",
                "statistic_value": 7,
            },
        ],
        "primary_kpi": {"name": "Cashflow Actual vs Forecast"},
        "supporting_kpis": [{
            "name": "Competitor Launches by Detection Source",
        }],
    })

    markdown = report["markdown_report"]
    assert "Latest Actual: AED 8M" in markdown
    assert "Latest Forecast: AED 10M" in markdown
    assert "Current Launch Count: 7" in markdown


@pytest.mark.asyncio
async def test_report_resolves_project_and_aging_data_from_nested_widgets():
    report = await ReportService().generate_report({
        "query": "What is the impact of a 90-day delay?",
        "scenario": {
            "description": "A 90-day delay to Horizon Heights would postpone handover.",
            "target_entity": "Horizon Heights",
        },
        "dashboard_data": {
            "widgets": [{
                "title": "Project Milestones",
                "data": {
                    "rows": [{
                        "project_name": "Horizon Heights",
                        "location": "Dubai",
                        "planned_handover_date": "2026-12-01",
                        "construction_status": "Under Construction",
                    }],
                },
            }],
            "stat_cards": [{
                "title": "Projects Nearing Handover",
                "value": 4,
            }],
            "table_records": [{
                "bucket": "90+",
                "count": 11,
            }],
        },
        "primary_kpi": {"name": "Projects Nearing Handover"},
        "supporting_kpis": [{"name": "AP Aging Buckets"}],
        "primary_risk": {
            "name": "Revenue Recognition Delay",
            "business_impact": "Deferred handover can postpone revenue recognition.",
        },
        "selected_actions": [{
            "title": "Approve schedule recovery",
            "action": "Prioritize critical-path recovery and customer communication.",
            "expected_outcome": "Reduce handover slippage and protect customer commitments.",
        }],
    })

    markdown = report["markdown_report"]
    assert "Project: Horizon Heights" in markdown
    assert "Location: Dubai" in markdown
    assert "Target Handover: 2026-12-01" in markdown
    assert "Status: Under Construction" in markdown
    assert "4" in markdown
    assert "90+ day bucket contains 11" in markdown
    assert "A 90-day delay to Horizon Heights" in report["executive_summary"]
    assert "most important indicator" in report["executive_summary"]
    assert "greatest business risk" in report["executive_summary"]
    assert "Leadership should prioritize" in report["executive_summary"]
    assert 80 <= len(report["executive_summary"].split()) <= 120
    assert len(report["executive_conclusion"].split(". ")) == 3
    assert "selected KPI" not in markdown.casefold()
    assert "decision signal" not in markdown.casefold()


@pytest.mark.asyncio
async def test_report_uses_latest_chart_series_values():
    report = await ReportService().generate_report({
        "widget_data": {
            "chart_series": [
                {"name": "Actual", "values": [5, 8]},
                {"name": "Forecast", "values": [9, 10]},
                {"name": "Variance", "values": [1, 2]},
                {"name": "Competitor Launches", "values": [3, 7]},
            ],
        },
        "primary_kpi": {"name": "Cashflow Actual vs Forecast"},
        "supporting_kpis": [{"name": "Competitor Launches"}],
    })

    markdown = report["markdown_report"]
    assert "Latest Actual: 8" in markdown
    assert "Latest Forecast: 10" in markdown
    assert "Variance: 2" in markdown
    assert "Current Launch Count: 7" in markdown


@pytest.mark.asyncio
async def test_kpi_insights_enriches_without_reselecting(monkeypatch):
    selected = {"name": "Competitor Launches", "value": 4}
    supporting = [{"name": "News Sentiment", "value": -0.1}]
    monkeypatch.setattr(
        KPIInsightsClient,
        "get_kpis",
        AsyncMock(return_value=({"kpis": [{"name": "Higher Confidence", "value": 8}]}, {})),
    )
    monkeypatch.setattr(
        KPIInsightsClient,
        "get_insights_stats",
        AsyncMock(return_value={}),
    )
    state = {
        "primary_kpi": selected,
        "supporting_kpis": supporting,
        "strict_dashboard_filter": False,
        "dashboard_kpi_records": [],
    }

    await kpi_insights_node(state)

    assert state["primary_kpi"] is selected
    assert state["supporting_kpis"] is supporting


@pytest.mark.asyncio
async def test_semantic_reasoning_can_refine_selector_owned_kpis(monkeypatch):
    class SemanticService:
        async def reason(self, **kwargs):
            return {
                "primary_kpi": {"name": "Sentiment"},
                "supporting_kpis": [{"name": "Competitor Launches"}],
            }

    monkeypatch.setattr(
        semantic_node_module,
        "SemanticReasoningService",
        SemanticService,
    )
    candidates = [
        {"name": "Sentiment", "value": -0.5, "source": "dashboard"},
        {"name": "Competitor Launches", "value": 7, "source": "dashboard"},
    ]
    state = {
        "dashboard_kpi_records": candidates,
        "dashboard_widget_kpis": [],
        "kpi_insights": {"kpis": []},
        "primary_kpi": {"name": "Legacy selection"},
        "supporting_kpis": [],
    }

    await semantic_node_module.semantic_reasoning_node(state)

    assert state["primary_kpi"] == {
        "name": "Sentiment",
        "value": -0.5,
        "source": "dashboard",
    }
    assert state["supporting_kpis"] == [{
        "name": "Competitor Launches",
        "value": 7,
        "source": "dashboard",
    }]


@pytest.mark.asyncio
async def test_semantic_risks_and_actions_win_over_fallbacks():
    primary_risk = {"name": "Semantic risk", "severity": "HIGH"}
    secondary_risk = {"name": "Semantic secondary risk", "severity": "MEDIUM"}
    semantic_actions = [{"title": "Semantic action"}]

    class UnexpectedRiskFallback:
        def select_risks(self, state):
            raise AssertionError("semantic risk should suppress fallback")

    class UnexpectedActionFallback:
        def select_actions(self, state):
            raise AssertionError("semantic action should suppress fallback")

    state = {
        "semantic_reasoning": {
            "primary_risk": primary_risk,
            "secondary_risk": secondary_risk,
            "actions": semantic_actions,
        },
        "selected_actions": [{"title": "Stale legacy action"}],
    }
    await risk_selector_node(state, service=UnexpectedRiskFallback())
    await action_selector_node(state, service=UnexpectedActionFallback())

    assert state["primary_risk"] is primary_risk
    assert state["secondary_risk"] is secondary_risk
    assert state["selected_actions"] is semantic_actions


def test_fallback_risk_and_actions_are_category_agnostic():
    initial = {
        "dashboard_category": "LAND_FEASIBILITY",
        "dashboard_semantics": {"widget_titles": ["Weighted Score"]},
        "scenario_semantics": {"change": "indicator decreases"},
        "primary_kpi": {"name": "Weighted Score"},
        "supporting_kpis": [{"name": "Return Index"}],
        "primary_business_entity": "Asset A",
    }
    category_changed = {**initial, "dashboard_category": "PROJECT_DELIVERY"}

    risk_service = RiskSelectorService()
    first_risks = risk_service.select_risks(initial)
    second_risks = risk_service.select_risks(category_changed)

    assert first_risks == second_risks
    assert first_risks["primary_risk"]["name"] == "Weighted Score Impact Risk"
    initial.update(first_risks)
    actions = ActionSelectorService().select_actions(initial)
    assert actions
    assert all("Weighted Score" in item["action"] for item in actions)
    assert all("Capital Allocation" not in item["title"] for item in actions)


def test_kpi_ranking_does_not_change_with_dashboard_category():
    candidates = [
        {"name": "Competitor Launches", "value": 12, "confidence_score": 0.6},
        {"name": "News Sentiment", "value": -0.3, "confidence_score": 0.9},
    ]
    common = {
        "candidates": candidates,
        "scenario_text": "competitor launches increase as news sentiment declines",
        "target_entity": "",
        "allowed_terms": [],
        "dashboard_themes": ["competition", "market_sentiment"],
        "scenario_themes": ["competition", "market_sentiment"],
        "dashboard_kpi_names": ["Competitor Launches", "News Sentiment"],
    }
    first = rank_kpis_by_formula(dashboard_category="LAND_FEASIBILITY", **common)
    second = rank_kpis_by_formula(dashboard_category="PROJECT_DELIVERY", **common)

    assert first == second


@pytest.mark.asyncio
async def test_catalog_and_recommendation_nodes_do_not_replace_selected_actions(monkeypatch):
    selected = [{"title": "Semantic response"}]
    monkeypatch.setattr(
        ActionsClient,
        "get_actions",
        AsyncMock(return_value=[{"title": "Catalog action"}]),
    )
    monkeypatch.setattr(
        ActionsClient,
        "get_action_stats",
        AsyncMock(return_value={}),
    )
    state = {
        "selected_actions": selected,
        "actions": selected,
    }

    await actions_node(state)
    await recommendation_node(state)

    assert state["available_actions"] == [{"title": "Catalog action"}]
    assert state["actions"] is selected
    assert state["selected_actions"] is selected
    assert state["recommendations"] == selected
