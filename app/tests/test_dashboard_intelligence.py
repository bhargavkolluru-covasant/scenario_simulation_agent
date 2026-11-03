import sys
import types
import json
import re

import pytest

from app.nodes.dashboard_node import _extract_widget_rows, dashboard_node
from app.nodes.dashboard_context_resolver_node import dashboard_context_resolver_node
from app.nodes.entity_matching_node import entity_matching_node
from app.nodes.kpi_insights_node import kpi_insights_node
from app.nodes.relevant_kpi_selector_node import relevant_kpi_selector_node
from app.clients.dashboard_client import DashboardClient
from app.services.entity_matching_service import EntityMatchingService
from app.services.impact_analysis_service import ImpactAnalysisService
from app.services.report_service import ReportService
from app.services.dashboard_intelligence_service import (
    DASHBOARD_TAXONOMY,
)
from app.services.simulation_service import SimulationService
from app.clients.kpi_insights_client import KPIInsightsClient
from unittest.mock import AsyncMock


def test_extract_widget_rows_preserves_row_objects():
    row = {"reference": "Orion", "details": {"rating": "Elevated"}}
    payload = {
        "widgets": [
            {"data": {"rows": [row]}},
            {"data": {"rows": [{"reference": "Other"}]}},
        ]
    }

    rows = _extract_widget_rows(payload)

    assert rows == [row, {"reference": "Other"}]
    assert rows[0] is row


@pytest.mark.asyncio
async def test_dashboard_node_loads_raw_payload_and_all_widget_rows(monkeypatch):
    rows = [{"entity_ref": "Orion"}, {"entity_ref": "Other"}]
    payload = {"widgets": [{"data": {"rows": rows}}]}
    monkeypatch.setattr(
        DashboardClient,
        "get_dashboard_data",
        AsyncMock(return_value=payload),
    )
    monkeypatch.setattr(
        DashboardClient,
        "get_dashboard",
        AsyncMock(return_value={"title": "Project Delivery Dashboard"}),
    )
    state = {"dashboard_id": "dashboard-1"}

    await dashboard_node(state)

    assert state["dashboard_data"] is payload
    assert state["dashboard_definition"]["title"] == "Project Delivery Dashboard"
    assert state["dashboard_rows"] == rows
    assert state["dashboard_rows"][0] is rows[0]


@pytest.mark.asyncio
async def test_dashboard_context_and_kpi_selector_resolve_land_feasibility():
    state = {
        "query": "Which approved development options should be prioritized if available investment capital is reduced by 30%?",
        "scenario": {"change_type": "investment capital reduction"},
        "dashboard_definition": {
            "title": "Land Feasibility Dashboard",
            "sections": [{"title": "Development Options"}],
            "widgets": [
                {"title": "HBU Options"},
                {"title": "Weighted Score"},
                {"title": "IRR and GDV"},
                {"title": "Hurdle Rate and Zoning Confidence"},
            ],
        },
        "dashboard_data": {
            "widgets": [{
                "title": "Approved Options",
                "data": {"rows": [
                    {
                        "option_id": "OPT-0003",
                        "hbu_option": "Mixed-use development",
                        "weighted_score": 11.29,
                        "irr": "18%",
                        "gdv": "AED 120M",
                        "development_cost": "AED 70M",
                        "hurdle_rate": "12%",
                        "zoning_confidence": "High",
                    },
                    {
                        "option_id": "OPT-0021",
                        "hbu_option": "Residential development",
                        "weighted_score": 10.4,
                        "irr": "15%",
                        "hurdle_rate": "12%",
                    },
                ]},
            }],
        },
        "dashboard_rows": [
            {
                "option_id": "OPT-0003",
                "hbu_option": "Mixed-use development",
                "weighted_score": 11.29,
                "irr": "18%",
                "gdv": "AED 120M",
                "development_cost": "AED 70M",
                "hurdle_rate": "12%",
                "zoning_confidence": "High",
            },
            {
                "option_id": "OPT-0021",
                "hbu_option": "Residential development",
                "weighted_score": 10.4,
                "irr": "15%",
                "hurdle_rate": "12%",
            },
        ],
    }

    await dashboard_context_resolver_node(state)
    await relevant_kpi_selector_node(state)

    assert state["dashboard_category"] == "LAND_FEASIBILITY"
    assert state["dashboard_context"]["category_resolved"] is True
    assert state["allowed_kpi_groups"] == DASHBOARD_TAXONOMY["LAND_FEASIBILITY"]["kpi_groups"]
    assert "Blacklisted Vendors" not in state["selected_dashboard_kpi_names"]
    assert {"hbu options", "weighted score", "irr"} <= {
        name.casefold() for name in state["selected_dashboard_kpi_names"]
    }
    assert state["strict_dashboard_filter"] is True


def test_entity_matching_searches_nested_values_case_insensitively():
    rows = [
        {"record_id": 1, "details": {"entity": "Orion Manufacturing"}},
        {"record_id": 2, "details": {"entity": "Unrelated"}},
        {"record_id": 3, "notes": ["Review ORION MANUFACTURING immediately"]},
    ]

    assert EntityMatchingService().match("orion manufacturing", rows) == [
        rows[0],
        rows[2],
    ]


@pytest.mark.asyncio
async def test_entity_matching_node_stores_records_and_summary():
    matching_row = {"reference": "Orion"}
    state = {
        "scenario": {"target_entity": "orion"},
        "dashboard_rows": [matching_row, {"reference": "Other"}],
    }

    await entity_matching_node(state)

    assert state["matched_dashboard_records"] == [matching_row]
    assert state["entity_match_summary"] == {
        "target_entity": "orion",
        "dashboard_record_count": 2,
        "matched_record_count": 1,
        "entity_match_count": 1,
    }


@pytest.mark.asyncio
async def test_simulation_uses_only_entity_matched_dashboard_rows():
    matching_row = {"entity": "Orion", "untyped_value": 100}
    unrelated_row = {"entity": "Unrelated", "untyped_value": 900}
    state = {
        "query": "Evaluate Orion risk",
        "scenario": {"target_entity": "Orion", "change_percentage": 10},
        "dashboard_rows": [matching_row, unrelated_row],
        "matched_dashboard_records": [matching_row],
        "entity_match_summary": {
            "target_entity": "Orion",
            "dashboard_record_count": 2,
            "matched_record_count": 1,
            "entity_match_count": 1,
        },
        "kpi_insights": {"kpis": [{"name": "Risk Score", "value": 40}]},
        "actions": [],
        "action_stats": {},
        "rules": [],
        "knowledge_graph_data": {},
    }

    result = await SimulationService().run(state)

    assert state["matched_dashboard_records"] == [matching_row]
    assert state["entity_match_summary"]["entity_match_count"] == 1
    assert result["dashboard_records"] == [matching_row]
    assert result["parameters"]["dashboard_records_count"] == 2
    assert result["parameters"]["matched_records_count"] == 1
    assert "Dashboard Records Evaluated: 2" in result["summary"]


@pytest.mark.asyncio
async def test_kpi_node_normalizes_recent_kpis_and_preserves_payload(monkeypatch):
    payload = {
        "kpi_summary": {
            "recent_kpis": [{
                "name": "Policy Exceptions",
                "value": 3,
                "confidence_score": 0.92,
                "reasoning": "Exceptions increased.",
            }]
        }
    }
    stats = {"total_kpis": 1}
    monkeypatch.setattr(
        KPIInsightsClient,
        "get_kpis",
        lambda self: _async_value(payload),
    )
    monkeypatch.setattr(
        KPIInsightsClient,
        "get_insights_stats",
        lambda self: _async_value(stats),
    )
    state = {}

    await kpi_insights_node(state)

    assert state["kpi_insights"] == {
        "raw": payload,
        "kpis": payload["kpi_summary"]["recent_kpis"],
        "stats": stats,
    }


@pytest.mark.asyncio
async def test_kpi_node_filters_enterprise_metrics_to_resolved_dashboard(monkeypatch):
    payload = {"kpis": [
        {"name": "IRR", "value": 18, "confidence_score": 0.6},
        {"name": "Weighted Score", "value": 11.29},
        {"name": "Blacklisted Vendors", "value": 8, "confidence_score": 0.99},
        {
            "name": "Compliance Findings",
            "value": 4,
            "causal_relationship": "Documented effect on zoning approval.",
        },
    ]}
    monkeypatch.setattr(
        KPIInsightsClient,
        "get_kpis",
        lambda self: _async_value(payload),
    )
    monkeypatch.setattr(
        KPIInsightsClient,
        "get_insights_stats",
        lambda self: _async_value({"total_kpis": 4}),
    )
    state = {
        "dashboard_category": "LAND_FEASIBILITY",
        "strict_dashboard_filter": True,
        "allowed_kpi_terms": DASHBOARD_TAXONOMY["LAND_FEASIBILITY"]["kpi_terms"],
        "selected_dashboard_kpi_names": ["IRR", "Weighted Score"],
        "dashboard_kpi_records": [{
            "name": "Development Cost",
            "value": "AED 70M",
            "dashboard_evidence": True,
        }],
    }

    await kpi_insights_node(state)

    assert {
        item["name"] for item in state["kpi_insights"]["kpis"]
    } == {"IRR", "Weighted Score", "Development Cost"}
    assert state["causal_support_kpis"] == [{
        **payload["kpis"][3],
        "causal_support_only": True,
    }]


async def _async_value(value):
    return value


@pytest.mark.asyncio
async def test_report_renders_matched_rows_and_kpi_sections():
    matched = [
        {"entity_ref": "Orion", "risk_indicator": "High"},
        {"related_entity": "Orion", "review_count": 4},
    ]
    report = await ReportService().generate_report({
        "query": "Evaluate Orion",
        "scenario": {"target_entity": "Orion"},
        "dashboard_rows": matched + [{"entity_ref": "Other"}],
        "matched_dashboard_records": matched,
        "entity_match_summary": {
            "target_entity": "Orion",
            "entity_match_count": 2,
        },
        "kpi_insights": {
            "raw": {"kpi_summary": {"recent_kpis": []}},
            "kpis": [{
                "name": "Policy Exceptions",
                "value": 3,
                "confidence_score": 0.92,
                "reasoning": "Exceptions increased.",
            }],
            "stats": {"total_kpis": 1},
        },
        "primary_kpi": {
            "name": "Policy Exceptions",
            "value": 3,
            "why_it_matters": "Exceptions increased.",
        },
        "primary_risk": {
            "name": "Policy Control Risk",
            "severity": "HIGH",
            "business_impact": "Exceptions may impair control effectiveness.",
        },
        "selected_actions": [{"title": "Review policy exceptions"}],
        "simulation_result": {"metrics": {}, "summary": "Completed."},
        "impact_result": {},
        "recommendations": [],
        "actions": [],
        "action_stats": {},
    })

    markdown = report["markdown_report"]
    assert "Dashboard Records Evaluated:" not in markdown
    assert "Matched Records:" not in markdown
    assert "Entity Match Count:" not in markdown
    assert "Policy Exceptions" in markdown
    assert "Exceptions may impair control effectiveness." in markdown
    assert "## Executive Summary" in markdown
    assert "## Primary KPI" in markdown
    assert "## Primary Risk" in markdown
    assert "## Recommended Actions" in markdown
    assert "Top KPI Insights" not in markdown
    assert "Top Risks" not in markdown
    assert "Top Actions" not in markdown
    assert "No structured KPI records were returned" not in markdown
    assert report["primary_kpi"]["name"] == "Policy Exceptions"
    assert len(report["supporting_kpis"]) <= 2
    assert len(report["selected_actions"]) <= 3
    assert "top_reasoning" not in report
    assert "top_confidence_scores" not in report
    assert "confidence_scores" not in report
    assert "Matched Record 1" not in markdown


@pytest.mark.asyncio
async def test_explainability_prompt_uses_business_evidence_and_returns_narrative(monkeypatch):
    class MockLLM:
        is_configured = True

        async def generate_json(self, prompt, system_instruction, schema=None):
            self.prompt = prompt
            assert schema is None
            return {
                "executive_summary": "Delivery commitments may be at risk.",
                "current_business_context": "Horizon Heights is under construction.",
                "business_impact": "A delay may affect buyer commitments.",
                "financial_impact": "Additional schedule pressure may raise costs.",
                "operational_impact": "Recovery planning is needed.",
                "key_risks": ["Schedule slippage", "Cost escalation"],
                "recommended_response": "Review recovery milestones.",
                "executive_conclusion": "Overall impact is Medium.",
            }

    llm = MockLLM()
    state = {
        "query": "What if Horizon Heights handover is delayed by 90 days?",
        "scenario": {"target_entity": "Horizon Heights"},
        "matched_dashboard_records": [{
            "entity": "Horizon Heights",
            "planned_handover": "2026-12-01",
        }],
        "kpi_insights": {
            "kpis": [{"kpi_name": "Cost Variance", "value": "High"}],
        },
        "rules": [{"name": "Handover escalation", "severity": "HIGH"}],
        "primary_kpi": {"name": "Cost Variance", "value": "High"},
        "primary_risk": {
            "name": "Schedule Slippage Risk",
            "business_impact": "A delay may affect delivery commitments.",
        },
        "selected_actions": [{"title": "Prepare schedule recovery plan"}],
        "impact_result": {"overall_severity": "MEDIUM", "dimensions": []},
        "simulation_result": {"metrics": {}},
    }

    llm_gateway = types.ModuleType("app.services.llm_gateway")
    llm_gateway.LLMGateway = type(
        "LLMGateway",
        (),
        {"get_service": classmethod(lambda cls: None)},
    )
    monkeypatch.setitem(sys.modules, "app.services.llm_gateway", llm_gateway)
    from app.services.explainability_service import ExplainabilityService

    result = await ExplainabilityService(llm_service=llm).explain(state)

    assert "Horizon Heights" in llm.prompt
    assert "Cost Variance" in llm.prompt
    assert "Handover escalation" not in llm.prompt
    assert "Prepare schedule recovery plan" in llm.prompt
    assert "Do not mention KPI counts" in llm.prompt
    assert "Executive context:" in llm.prompt
    assert "Matched Business Context:" not in llm.prompt
    assert result["current_business_context"] == "Horizon Heights is under construction."
    assert result["key_risks"] == [
        "Schedule Slippage Risk: A delay may affect delivery commitments."
    ]
    assert result["executive_conclusion"] == "Overall impact is Medium."


@pytest.mark.asyncio
async def test_explainability_prompt_is_bounded_and_uses_only_summarized_context():
    from app.services.explainability_service import (
        ExplainabilityService,
        _estimate_tokens,
        build_executive_context,
    )

    raw_sentinel = "RAW_PRIVATE_DASHBOARD_PAYLOAD_" + ("Z" * 8000)

    class CapturingLLM:
        is_configured = True
        prompt = ""
        system_instruction = ""

        async def generate_json(self, prompt, system_instruction, schema=None):
            self.prompt = prompt
            self.system_instruction = system_instruction
            return {}

    llm = CapturingLLM()
    state = {
        "query": "What if operating performance declines?",
        "scenario": {"description": "Performance decreases by 20%"},
        "dashboard_rows": [
            {
                "entity": "Operations",
                "status": raw_sentinel,
                "raw_blob": raw_sentinel,
            }
            for _ in range(100)
        ],
        "kpi_insights": {
            "kpis": [
                {
                    "kpi_name": f"Production throughput {index}",
                    "kpi_value": 100 - index,
                    "reasoning": raw_sentinel,
                    "extra_raw": raw_sentinel,
                }
                for index in range(30)
            ]
        },
        "rules": [
            {"name": f"High risk rule {index}", "severity": "HIGH", "full_record": raw_sentinel}
            for index in range(30)
        ],
        "actions": [
            {"title": f"Mitigation action {index}", "description": raw_sentinel}
            for index in range(30)
        ],
        "impact_result": {
            "overall_severity": "HIGH",
            "dimensions": [
                {
                    "dimension_name": f"Risk dimension {index}",
                    "severity": "HIGH",
                    "impact_description": raw_sentinel,
                }
                for index in range(30)
            ],
            "root_cause_analysis": [
                {
                    "root_cause": f"Cause {index}",
                    "confidence": 0.9,
                    "evidence": [raw_sentinel],
                    "business_consequence": raw_sentinel,
                    "recommended_mitigation": raw_sentinel,
                }
                for index in range(30)
            ],
        },
        "simulation_result": {
            "metrics": {},
            "financial_model": {
                "current_exposure": {
                    "items": [
                        {
                            "name": f"Exposure {index}",
                            "formatted_amount": "AED 100",
                            "extra": raw_sentinel,
                        }
                        for index in range(30)
                    ]
                },
                "scenario_exposure": {
                    "severity": "HIGH",
                    "financial_reasoning": raw_sentinel,
                    "estimated_amount_by_currency": {"AED": 1000},
                    "impacts": [
                        {
                            "category": "OPERATIONAL",
                            "impact": f"Impact {index}",
                            "severity": "HIGH",
                            "extra": raw_sentinel,
                        }
                        for index in range(30)
                    ],
                    "assumptions": [raw_sentinel] * 30,
                },
                "combined_outlook": {
                    "severity": "HIGH",
                    "summary": raw_sentinel,
                    "total_by_currency": {"AED": 1100},
                },
            },
        },
    }

    context = build_executive_context(state)
    await ExplainabilityService(llm_service=llm).explain(state)

    assert set(context) == {
        "executive_summary",
        "key_business_context",
        "top_kpis",
        "top_risks",
        "top_actions",
        "financial_summary",
        "root_causes",
        "causal_analysis",
    }
    assert len(context["top_kpis"]) <= 5
    assert len(context["top_risks"]) <= 5
    assert len(context["top_actions"]) <= 5
    assert len(context["root_causes"]) <= 5
    assert _estimate_tokens(json.dumps(context, ensure_ascii=False)) <= 1500
    assert _estimate_tokens(llm.prompt + llm.system_instruction) <= 3000
    assert raw_sentinel not in llm.prompt
    assert "Executive context:" in llm.prompt

    from app.services.explainability_service import _complete_explanation

    long_text = " ".join(["business"] * 100)
    bounded = _complete_explanation({
        "executive_summary": long_text,
        "current_business_context": long_text,
        "business_impact": long_text,
        "financial_impact": long_text,
        "operational_impact": long_text,
        "key_risks": [long_text],
        "recommended_response": long_text,
        "executive_conclusion": long_text,
    })
    words = sum(
        len(item.split()) if isinstance(item, str)
        else sum(len(str(part).split()) for part in item)
        for item in bounded.values()
        if isinstance(item, (str, list))
    )
    assert words <= 400


@pytest.mark.asyncio
async def test_explainability_coerces_llm_field_format_variants():
    class MockLLM:
        is_configured = True

        async def generate_json(self, prompt, system_instruction, schema=None):
            return {
                "executive_summary": ["Delivery is at risk.", "Recovery is possible."],
                "current_business_context": None,
                "business_impact": ["Buyer commitments may be affected."],
                "financial_impact": None,
                "operational_impact": ["Review the delivery plan."],
                "key_risks": "Schedule slippage",
                "recommended_response": ["Action 1", "Action 2"],
                "executive_conclusion": None,
                "key_drivers": None,
                "risk_explanation": ["Cost and schedule exposure."],
                "recommendation_rationale": None,
            }

    from app.services.explainability_service import ExplainabilityService

    result = await ExplainabilityService(llm_service=MockLLM()).explain({
        "query": "What if delivery is delayed?",
        "scenario": {},
        "matched_dashboard_records": [],
        "kpi_insights": {},
        "rules": [],
        "primary_risk": {
            "name": "Selected schedule risk",
            "business_impact": "Schedule slippage is the selected risk.",
        },
        "selected_actions": [{"title": "Selected recovery action"}],
        "impact_result": {},
        "simulation_result": {"metrics": {}},
    })

    assert result["executive_summary"] == "Delivery is at risk.\nRecovery is possible."
    assert result["current_business_context"] == ""
    assert result["key_risks"] == [
        "Selected schedule risk: Schedule slippage is the selected risk."
    ]
    assert result["recommended_response"] == "Selected recovery action"
    assert result["executive_conclusion"] == ""
    assert result["key_drivers"] == ["Selected schedule risk"]
    assert result["risk_explanation"] == (
        "Selected schedule risk: Schedule slippage is the selected risk."
    )


@pytest.mark.asyncio
async def test_explainability_fallback_uses_business_language():
    class UnconfiguredLLM:
        is_configured = False

    from app.services.explainability_service import ExplainabilityService

    service = ExplainabilityService(llm_service=UnconfiguredLLM())
    explanation = await service.explain({
        "query": "What if Horizon Heights handover is delayed by 90 days?",
        "scenario": {"target_entity": "Horizon Heights"},
        "matched_dashboard_records": [{
            "entity": "Horizon Heights",
            "status": "Under construction",
            "planned_handover_date": "2026-12-01",
        }],
        "kpi_insights": {"kpis": []},
        "rules": [],
        "actions": [],
        "recommendations": [],
        "simulation_result": {
            "metrics": {"impact_probability": 0.175},
        },
        "impact_result": {
            "overall_severity": "MEDIUM",
            "overall_impact_score": 42,
            "dimensions": [{
                "dimension_name": "Scenario Impact",
                "severity": "MEDIUM",
                "impact_description": "Risk score is 42/100, probability is 17.5%.",
            }],
        },
    })

    assert "17.5%" not in str(explanation)
    assert "42/100" not in str(explanation)
    assert "moderate likelihood" in explanation["operational_impact"]
    assert "1 December 2026" in explanation["current_business_context"]
    assert explanation["executive_conclusion"].startswith("Overall impact is assessed as Medium")


@pytest.mark.asyncio
async def test_report_uses_explanation_and_hides_telemetry_scores():
    report = await ReportService().generate_report({
        "query": "What if Horizon Heights handover is delayed by 90 days?",
        "explanation": {
            "executive_summary": "Delivery commitments may be affected.",
            "current_business_context": "Horizon Heights is under construction.",
            "business_impact": "The delay may affect customer commitments.",
            "financial_impact": "Cost pressure may increase.",
            "operational_impact": "Schedule recovery planning is needed.",
            "key_risks": ["Schedule slippage may affect delivery commitments."],
            "recommended_response": "Establish recovery milestones.",
            "executive_conclusion": "Overall impact is Medium.",
        },
        "simulation_result": {"summary": "Dashboard Records Evaluated: 12"},
        "impact_result": {
            "overall_severity": "MEDIUM",
            "overall_impact_score": 42,
            "dimensions": [{
                "dimension_name": "Scenario Impact",
                "severity": "MEDIUM",
                "score": 42,
                "impact_description": (
                    "The modeled risk score is 42/100 and the impact probability is 30%."
                ),
            }],
        },
        "recommendations": [],
        "actions": [],
        "include_full_state": True,
    })

    markdown = report["markdown_report"]
    assert "delivery" not in report["executive_summary"].casefold()
    assert "**Situation:**" in markdown
    assert "**Business Impact:**" in markdown
    assert "**Decision Required:**" in markdown
    assert "**Expected Outcome:**" in markdown
    assert len(report["executive_summary"].split()) <= 120
    assert "Dashboard Records Evaluated: 12" not in markdown
    assert "42/100" not in markdown
    assert "30%" not in markdown
    assert "## Financial Impact" not in markdown
    assert "## Operational Impact" not in markdown


@pytest.mark.asyncio
async def test_report_does_not_select_kpis_from_raw_insights():
    kpis = [
        {"kpi_name": "KPI name", "kpi_value": 1},
        {"name": "Name", "value": 2},
        {"title": "Title", "current_value": 3},
        {"label": "Label", "metric_value": 4},
        {"metric": "Metric", "score": 5},
    ]
    report = await ReportService().generate_report({
        "explanation": {"executive_summary": "Summary"},
        "kpi_insights": {"kpis": kpis},
        "impact_result": {},
        "recommendations": [],
        "actions": [],
        "include_full_state": True,
    })

    assert report["primary_kpi"] is None
    assert report["supporting_kpis"] == []
    assert "top_kpi_insights" not in report


@pytest.mark.asyncio
async def test_report_uses_full_query_and_renders_currency_and_percent_once():
    query = "What would be the business and financial impact if average contract value changes by 51.81%?"
    report = await ReportService().generate_report({
        "query": query,
        "explanation": {
            "executive_summary": (
                "Accrued Unpaid Commissions is AED 25,234,246. Committed delivery and "
                "commercial performance warrant leadership review."
            ),
            "current_business_context": (
                "Accrued Unpaid Commissions AED 25,234,246 is elevated. "
                "The portfolio is exposed to contract-value volatility."
            ),
            "executive_conclusion": "Validate exposure and protect commercial commitments.",
        },
        "kpi_insights": {"kpis": [
            {
                "kpi_name": "Highest Contract Value Variance",
                "kpi_value": 51.81,
                "kpi_unit": "%",
                "reasoning": "Variance is elevated.",
                "confidence_score": 0.96,
            },
            {
                "kpi_name": "Accrued Unpaid Commissions",
                "kpi_value": 25_234_246,
                "kpi_unit": "AED",
                "reasoning": "Commissions remain unpaid.",
                "confidence_score": 0.91,
            },
        ]},
        "primary_kpi": {
            "name": "Highest Contract Value Variance",
            "value": "51.81%",
            "unit": "%",
            "why_it_matters": "Variance is elevated.",
            "confidence": 0.96,
        },
        "impact_result": {
            "overall_severity": "HIGH",
            "financial_model": {
                "existing_enterprise_exposure": {
                    "items": [{
                        "name": "Accrued Unpaid Commissions",
                        "formatted_amount": "AED 25,234,246",
                    }]
                },
                "scenario_incremental_exposure": {
                    "status": "not_quantified",
                    "expected_case": {},
                },
                "combined_risk_outlook": {
                    "financial_risk": "HIGH",
                    "liquidity_risk": "MEDIUM",
                    "revenue_risk": "UNQUANTIFIED",
                    "operational_risk": "LOW",
                    "total_by_currency": {"AED": 25_234_246},
                },
            },
        },
        "knowledge_graph_data": {"nodes": [], "edges": []},
        "graph_summary": {"graph_exists": False, "total_nodes": 0, "total_edges": 0},
        "include_full_state": True,
    })

    markdown = report["markdown_report"]
    assert report["title"] == "Executive Scenario Report"
    assert query in markdown
    assert "51.81%" in markdown
    assert markdown.count("Variance is elevated.") == 2
    assert report["primary_kpi"]["why_it_matters"] == "Variance is elevated."
    assert "Accrued Unpaid Commissions" not in markdown
    assert report["financial_impact"] is None
    assert "## Financial Impact" not in markdown
    assert len(report["executive_summary"].split()) <= 120
    assert "Knowledge Graph Findings" not in markdown
    assert "## Affected Entities" not in markdown
    assert "top_reasoning" not in report
    assert "confidence_scores" not in report
    assert "affected_entities" not in report
    assert "dependency_chains" not in report


@pytest.mark.asyncio
async def test_report_renders_graph_summary_and_blast_radius_only_when_available():
    report = await ReportService().generate_report({
        "query": "Assess the effect of a project schedule delay.",
        "graph_summary": {
            "graph_exists": True,
            "total_nodes": 3,
            "total_edges": 2,
            "node_types": {"Project": 1, "Supplier": 2},
            "relationship_types": {"DEPENDS_ON": 2},
            "impact_propagation_candidate_types": ["Supplier"],
            "explanation": "The project is linked to two supplier relationships.",
        },
        "related_entities": [{"name": "Supplier A"}],
        "dependency_paths": [{
            "entities": ["Project Alpha", "Supplier A"],
            "relationships": ["DEPENDS_ON"],
        }],
        "blast_radius": {
            "root_entity": "Project Alpha",
            "affected_entity_count": 1,
            "affected_entities": [{"name": "Supplier A"}],
            "affected_entities_by_type": {"Supplier": 1},
        },
        "include_full_state": True,
    })

    markdown = report["markdown_report"]
    assert "Graph coverage" not in markdown
    assert "Supplier A" not in markdown
    assert "knowledge_graph_findings" not in report
    assert "affected_entities" not in report
    assert "dependency_chains" not in report


@pytest.mark.asyncio
async def test_report_keeps_project_entity_and_business_causal_chain_central():
    report = await ReportService().generate_report({
        "query": "What if Horizon Heights handover is delayed by 90 days?",
        "scenario": {"target_entity": "Horizon Heights"},
        "entity_match_summary": {
            "target_entity": "Horizon Heights",
            "matched_record_count": 1,
        },
        "matched_dashboard_records": [{
            "project": "Horizon Heights",
            "status": "Handover at risk",
            "construction_status": "Behind schedule",
        }],
        "dashboard_data": {"project": "Horizon Heights", "status": "Behind schedule"},
        "kpi_insights": {"kpis": [
            {
                "kpi_name": "Blacklisted Vendors",
                "kpi_value": 8,
                "confidence_score": 0.99,
            },
            {
                "kpi_name": "Project Handover Delay",
                "kpi_value": 90,
                "unit": "days",
                "reasoning": "Horizon Heights construction handover is delayed.",
                "confidence_score": 0.72,
            },
        ]},
        "rules": [{"name": "Handover milestone escalation", "severity": "HIGH"}],
        "impact_result": {"overall_severity": "HIGH", "dimensions": []},
        "explanation": {
            "operational_impact": "Delivery milestones and customer handovers are exposed.",
        },
        "include_full_state": True,
    })

    markdown = report["markdown_report"]
    assert "A 90-day delay" not in report["executive_summary"]
    assert report["primary_kpi"] is None
    assert report["primary_risk"] is None
    assert report["selected_actions"] == []
    assert "Project Handover Delay" not in markdown
    assert "Handover milestone escalation" not in markdown
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} IST", report["generated_at"])


@pytest.mark.asyncio
async def test_report_resolves_primary_entity_from_dashboard_when_parser_has_none():
    report = await ReportService().generate_report({
        "query": "What if Horizon Heights handover is delayed by 90 days?",
        "scenario": {},
        "dashboard_rows": [{"project_name": "Horizon Heights"}],
    })

    assert "Horizon Heights" in report["business_query"]


@pytest.mark.asyncio
async def test_report_normalizes_duplicate_words_metadata_and_severity():
    report = await ReportService().generate_report({
        "query": "What if Horizon Heights handover handover is delayed?",
        "scenario": {"target_entity": "Horizon Heights"},
        "impact_result": {
            "overall_severity": "HIGH",
            "dimensions": [{
                "dimension_name": "Delivery",
                "severity": "MEDIUM",
                "impact_description": {
                    "title": "Title: Handover delay",
                    "consequence": (
                        "consequence: Horizon Heights handover handover may affect "
                        "customer commitments."
                    ),
                },
            }],
            "causal_analysis": {"scenario_category": "operational"},
        },
        "explanation": {
            "key_risks": [{
                "title": "Title: Enterprise Risk: Broad Reputational Impact",
                "consequence": (
                    "consequence: Horizon Heights handover handover may weaken buyer confidence."
                ),
            }],
        },
        "include_full_state": True,
    })

    markdown = report["markdown_report"]
    assert "Horizon Heights handover handover" not in markdown
    assert "title:" not in markdown.casefold()
    assert "consequence:" not in markdown.casefold()
    assert "Reputational Risk" not in markdown
    assert "Horizon Heights handover may" not in markdown
    assert report["primary_risk"] is None
    assert "## Executive Decision Required" in markdown


@pytest.mark.asyncio
async def test_operational_recommendations_rank_before_generic_compliance():
    report = await ReportService().generate_report({
        "query": "What if Horizon Heights schedule is delayed?",
        "scenario": {"target_entity": "Horizon Heights"},
        "recommendations": [
            {
                "title": "Complete compliance checklist",
                "priority": "CRITICAL",
                "business_value": "critical",
                "description": "Review policy and regulatory compliance.",
            },
            {
                "title": "Contractor performance review",
                "priority": "MEDIUM",
                "business_value": "moderate",
                "description": "Review contractor delivery performance.",
            },
            {
                "title": "Resource reallocation",
                "priority": "MEDIUM",
                "business_value": "moderate",
                "description": "Reallocate resources to critical path.",
            },
            {
                "title": "Schedule recovery plan",
                "priority": "MEDIUM",
                "business_value": "moderate",
                "description": "Recover the project schedule.",
            },
        ],
        "selected_actions": [
            {"title": "Schedule recovery plan"},
            {"title": "Resource reallocation"},
            {"title": "Contractor performance review"},
        ],
        "include_full_state": True,
    })

    action_titles = [item["title"] for item in report["selected_actions"]]
    assert action_titles == [
        "Schedule recovery plan",
        "Resource reallocation",
        "Contractor performance review",
    ]


@pytest.mark.asyncio
async def test_scenario_specific_kpi_ranks_above_generic_enterprise_risk():
    report = await ReportService().generate_report({
        "query": "What if Horizon Heights handover schedule is delayed?",
        "scenario": {"target_entity": "Horizon Heights"},
        "kpi_insights": {"kpis": [
            {
                "name": "Enterprise Risk",
                "value": 82,
                "category": "RISK",
                "confidence_score": 0.99,
            },
            {
                "name": "Handover Schedule Delay",
                "value": 90,
                "unit": "days",
                "category": "OPERATIONAL",
                "reasoning": "Horizon Heights handover schedule is delayed.",
                "confidence_score": 0.55,
            },
        ]},
        "primary_kpi": {
            "name": "Handover Schedule Delay",
            "value": 90,
            "unit": "days",
            "confidence": 0.55,
        },
        "include_full_state": True,
    })

    assert report["primary_kpi"]["name"] == "Handover Schedule Delay"
    assert "top_kpi_insights" not in report


@pytest.mark.asyncio
async def test_report_does_not_rank_or_generate_actions():
    report = await ReportService().generate_report({
        "recommendations": [
            {"title": "Low-risk action", "priority": "LOW", "business_value": "low", "effort": "high"},
            {"title": "Risk control", "priority": "HIGH", "business_value": "high", "effort": "low"},
            {"title": "Fast value", "priority": "MEDIUM", "business_value": "high", "effort": "easy"},
            {"title": "Action four", "priority": "MEDIUM"},
            {"title": "Action five", "priority": "LOW"},
            {"title": "Action six", "priority": "LOW"},
        ],
        "selected_actions": [
            {"title": "Low-risk action", "priority": "LOW"},
            {"title": "Risk control", "priority": "HIGH"},
        ],
        "include_full_state": True,
    })

    assert [item["title"] for item in report["selected_actions"]] == [
        "Low-risk action",
        "Risk control",
    ]


@pytest.mark.asyncio
async def test_report_does_not_rank_kpis_from_raw_insights():
    report = await ReportService().generate_report({
        "query": "What if customer satisfaction declines?",
        "scenario": {"description": "Customer experience deterioration"},
        "kpi_insights": {"kpis": [
            {
                "kpi_name": "Customer Satisfaction",
                "kpi_value": 2.8,
                "category": "CUSTOMER",
                "reasoning": "Customer satisfaction is below target.",
                "confidence_score": 0.55,
            },
            {
                "kpi_name": "Unrelated Cash Balance",
                "kpi_value": "USD 9M",
                "category": "FINANCIAL",
                "reasoning": "Cash balance is stable.",
                "confidence_score": 0.99,
            },
        ]},
        "matched_dashboard_records": [{
            "customer": "Northwind",
            "metric_name": "Customer Satisfaction",
        }],
        "impact_result": {
            "causal_analysis": {
                "scenario_category": "customer_experience",
                "primary_kpi": "Customer Satisfaction",
            },
        },
        "include_full_state": True,
    })

    assert report["primary_kpi"] is None
    assert report["supporting_kpis"] == []
    assert "top_kpi_insights" not in report


@pytest.mark.asyncio
async def test_report_does_not_rebuild_land_feasibility_decisions():
    rows = [
        {
            "option_id": "OPT-0003",
            "hbu_option": "Mixed-use development",
            "weighted_score": 11.29,
            "irr": "18%",
            "gdv": "AED 120M",
            "development_cost": "AED 70M",
            "hurdle_rate": "12%",
            "zoning_confidence": "High",
        },
        {
            "option_id": "OPT-0021",
            "hbu_option": "Residential development",
            "weighted_score": 10.4,
            "irr": "15%",
            "hurdle_rate": "12%",
        },
        {
            "option_id": "OPT-0009",
            "hbu_option": "Commercial development",
            "weighted_score": 9.8,
            "irr": "13%",
            "hurdle_rate": "12%",
        },
    ]
    report = await ReportService().generate_report({
        "query": (
            "Which approved development options should be prioritized if available "
            "investment capital is reduced by 30%?"
        ),
        "scenario": {
            "target_entity": "Land Parcel Alpha",
            "description": "Investment capital is reduced by 30%.",
        },
        "primary_business_entity": "Land Parcel Alpha",
        "dashboard_category": "LAND_FEASIBILITY",
        "dashboard_context": {
            "category": "LAND_FEASIBILITY",
            "category_resolved": True,
            "allowed_kpi_terms": DASHBOARD_TAXONOMY["LAND_FEASIBILITY"]["kpi_terms"],
            "kpi_names": ["Weighted Score", "IRR", "GDV", "Development Cost"],
        },
        "allowed_kpi_terms": DASHBOARD_TAXONOMY["LAND_FEASIBILITY"]["kpi_terms"],
        "selected_dashboard_kpi_names": [
            "Weighted Score", "IRR", "GDV", "Development Cost", "Hurdle Rate",
        ],
        "strict_dashboard_filter": True,
        "dashboard_rows": rows,
        "matched_dashboard_records": rows,
        "kpi_insights": {"kpis": [
            {
                "name": "Blacklisted Vendors",
                "value": 8,
                "confidence_score": 0.99,
                "reasoning": "Vendor exposure is high.",
            },
            {
                "name": "Weighted Score",
                "value": 11.29,
                "confidence_score": 0.65,
                "reasoning": "OPT-0003 has the highest weighted feasibility score.",
            },
            {
                "name": "IRR",
                "value": 18,
                "unit": "%",
                "confidence_score": 0.6,
                "reasoning": "The leading option remains above the 12% hurdle rate.",
            },
            {
                "name": "Development Cost",
                "value": 70,
                "unit": "AED M",
                "confidence_score": 0.8,
                "reasoning": "Cost remains within the investment ceiling.",
            },
        ]},
        "actions": [{
            "title": "Complete compliance checklist",
            "priority": "CRITICAL",
        }],
        "impact_result": {"overall_severity": "HIGH"},
    })

    markdown = report["markdown_report"]
    assert report["primary_kpi"] is None
    assert report["supporting_kpis"] == []
    assert report["primary_risk"] is None
    assert report["selected_actions"] == []
    assert "Blacklisted Vendors" not in markdown
    assert "Complete compliance checklist" not in markdown
    assert "Capital Allocation Risk" not in markdown
    expected_sections = [
        "## Executive Summary",
        "## Executive Decision Required",
        "## Primary KPI",
        "## Supporting KPIs",
        "## Primary Risk",
        "## Secondary Risk",
        "## Recommended Actions",
        "## Executive Conclusion",
    ]
    positions = [markdown.index(section) for section in expected_sections]
    assert positions == sorted(positions)
    assert "Dashboard Category: Land Feasibility" not in markdown
    assert "## Financial Impact" not in markdown
    assert "Formula:" not in markdown


@pytest.mark.asyncio
async def test_impact_assessment_keeps_kpi_exposure_separate_from_scenario_loss():
    impact = await ImpactAnalysisService().analyze({
        "simulation_result": {
            "metrics": {
                "baseline_financial_exposure": 0,
                "simulated_financial_exposure": 0,
            }
        },
        "kpi_insights": {"kpis": [
            {
                "kpi_name": "Accrued Unpaid Commissions",
                "kpi_value": 25_234_246,
                "kpi_unit": "AED",
            },
            {
                "kpi_name": "Highest Contract Value Variance",
                "kpi_value": 51.81,
                "kpi_unit": "%",
            },
            {
                "kpi_name": "Budget Overrun",
                "kpi_value": 3_500_000,
                "kpi_unit": "AED",
            },
        ]},
        "knowledge_graph_data": {"nodes": [], "edges": []},
    })

    assert impact["financial_exposure_source"] == "unquantified"
    assert impact["financial_exposure_at_risk"] == 0
    assert {item["category"] for item in impact["financial_exposure_evidence"]} == {
        "Current Enterprise Exposure",
    }
    assert {
        item["value"] for item in impact["financial_exposure_evidence"]
    } == {"AED 25,234,246", "AED 3,500,000"}
    assert "confidence_scores" not in impact
    assert "kpi_reasoning" not in impact
