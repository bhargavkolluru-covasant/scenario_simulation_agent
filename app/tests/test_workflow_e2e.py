import asyncio
import pytest
from unittest.mock import AsyncMock

from app.clients.base_client import BaseClient
from app.clients.actions_client import ActionsClient
from app.clients.dashboard_client import DashboardClient
from app.clients.kpi_insights_client import KPIInsightsClient
from app.clients.knowledge_graph_client import KnowledgeGraphClient
from app.clients.rules_client import RulesClient
from app.config.settings import settings
from app.services.scenario_parser_service import ScenarioParserService
from app.nodes.context_node import context_node
from app.graph.workflow import workflow


@pytest.mark.asyncio
async def test_context_node_uses_enterprise_and_domain_without_scope():
    result = await context_node({
        "enterprise_id": "enterprise-test",
        "domain_ids": ["domain-test"],
    })

    assert result["context"] == {
        "enterprise_id": "enterprise-test",
        "domain_ids": ["domain-test"],
        "scope_id": settings.scope_id or "",
    }


@pytest.mark.asyncio
async def test_platform_clients_use_confirmed_routes_and_tenant_headers(monkeypatch):
    calls = []

    async def fake_get(self, endpoint, params=None, headers=None):
        calls.append(endpoint)
        if endpoint.endswith("/data"):
            return {"projects": []}
        if endpoint.endswith("/kpis"):
            return {"kpis": [{"name": "On-time delivery", "value": 0.95}]}
        if endpoint.endswith("/actions"):
            return {"data": {"actions": []}}
        if endpoint.endswith("/insights-stats"):
            return {"total_kpis": 1}
        if endpoint == "/api/v1/dashboards/dashboard-1":
            return {}
        return {"total_actions": 0}

    monkeypatch.setattr(BaseClient, "get", fake_get)
    dashboard_client = DashboardClient(base_url="https://platform.example")
    kpi_client = KPIInsightsClient(base_url="https://platform.example")
    actions_client = ActionsClient(base_url="https://platform.example")

    assert await dashboard_client.get_dashboard_data("dashboard-1") == {"projects": []}
    assert await dashboard_client.get_dashboard("dashboard-1") == {}
    assert await kpi_client.get_kpis() == {
        "kpis": [{"name": "On-time delivery", "value": 0.95}]
    }
    assert await kpi_client.get_insights_stats() == {"total_kpis": 1}
    assert await actions_client.get_actions() == []
    assert await actions_client.get_action_stats() == {"total_actions": 0}
    assert calls == [
        "/api/v1/dashboards/dashboard-1/data",
        "/api/v1/dashboards/dashboard-1",
        "/api/v1/metrics/insights/kpis",
        "/api/v1/metrics/insights-stats",
        "/api/v1/metrics/insights/actions",
        "/api/v1/metrics/actions-stats",
    ]
    assert dashboard_client._get_headers()["X-Enterprise-Id"] == settings.ARIIA_ENTERPRISE_ID
    assert dashboard_client._get_headers()["X-Domain-Id"] == ",".join(settings.domain_ids)
    assert BaseClient(
        base_url="https://platform.example",
        auth_token="integration-test-token",
    )._get_headers()["Authorization"] == "Bearer integration-test-token"
    scoped_client = DashboardClient(
        base_url="https://platform.example",
        enterprise_id="enterprise-override",
        domain_ids=["domain-override"],
        scope_id="legacy-scope",
    )
    assert scoped_client._get_headers()["X-Enterprise-Id"] == "enterprise-override"
    assert scoped_client._get_headers()["X-Domain-Id"] == "domain-override"
    assert scoped_client._get_headers()["X-Scope-Id"] == "legacy-scope"


@pytest.mark.asyncio
async def test_full_simulation_workflow(monkeypatch):
    print("\n================== Testing Full Simulation Agent Workflow ==================")
    monkeypatch.setattr(
        ScenarioParserService,
        "parse",
        AsyncMock(return_value={
            "scenario_type": "operational_delay",
            "target_entity": "Acme Project",
            "change_type": "delivery_delay",
            "change_percentage": 20,
            "time_horizon": "next quarter",
            "domain": "operations",
            "description": "Test operational delay scenario",
        }),
    )
    monkeypatch.setattr(
        DashboardClient,
        "get_dashboard_data",
        AsyncMock(return_value={
            "widgets": [{
                "data": {
                    "rows": [{
                        "entity_reference": "Acme Project",
                        "risk_rating": "At Risk",
                        "forecast_date": "2026-12-01",
                        "budget": 100000,
                    }]
                }
            }]
        }),
    )
    monkeypatch.setattr(
        DashboardClient,
        "get_dashboard",
        AsyncMock(return_value={"id": "test-dashboard"}),
    )
    monkeypatch.setattr(
        KPIInsightsClient,
        "get_kpis",
        AsyncMock(return_value={
            "kpis": [
                {
                    "name": "Construction Risk",
                    "value": 65,
                    "reasoning": "Schedule dependencies are behind plan.",
                    "confidence_score": 0.91,
                },
                {"name": "Budget Overrun", "value": 12000},
            ]
        }),
    )
    monkeypatch.setattr(
        KPIInsightsClient,
        "get_insights_stats",
        AsyncMock(return_value={"total_kpis": 2}),
    )
    monkeypatch.setattr(
        ActionsClient,
        "get_actions",
        AsyncMock(return_value=[
            {
                "action_id": "ACT-1",
                "title": "Review schedule recovery plan",
                "priority": "HIGH",
            }
        ]),
    )
    monkeypatch.setattr(
        ActionsClient,
        "get_action_stats",
        AsyncMock(return_value={"critical_actions": 1, "overdue_actions": 0}),
    )
    monkeypatch.setattr(
        RulesClient,
        "get_rules",
        AsyncMock(return_value={"rules": []}),
    )
    monkeypatch.setattr(
        KnowledgeGraphClient,
        "get_knowledge_graph",
        AsyncMock(return_value={"nodes": [], "edges": [], "stats": {}}),
    )

    initial_state = {
        "query": "Simulate a construction delay for Acme Project",
        "scope_id": "test-scope",
        "dashboard_id": "test-dashboard",
        "semantic_entities": [],
    }

    result = await workflow.ainvoke(initial_state)

    print("Workflow Execution Finished.")
    print("Status:", result.get("status"))
    print("Current Node:", result.get("current_node"))

    final_report = result.get("final_report", {})
    print("Report ID:", final_report.get("report_id"))
    print("Report Title:", final_report.get("title"))
    print("Executive Summary:", final_report.get("executive_summary")[:200], "...")
    print("Total Recommendations:", len(result.get("recommendations", [])))

    assert "final_report" in result, "final_report must be present in workflow output"
    assert "report_id" in final_report, "Report must contain report_id"
    assert "simulation_result" in result, "simulation_result must be present in workflow output"
    assert "impact_result" in result, "impact_result must be present in workflow output"
    assert "recommendations" in result, "recommendations must be present in workflow output"
    assert "scenario" in result, "scenario must be present in workflow output"
    assert "dashboard_data" in result, "dashboard context must be present"
    assert "kpi_insights" in result, "KPI insights must be present"
    assert "actions" in result, "recommended actions must be present"
    assert "action_stats" in result, "action statistics must be present"
    assert not any(
        recommendation.get("action_type") == "SUPPLY_CHAIN_REDIRECTION"
        for recommendation in result["recommendations"]
    ), "project-risk scenarios must not invent supplier actions"
    assert result["simulation_result"]["metrics"]["risk_score"] > 0
    assert result["dashboard_rows"] == [{
        "entity_reference": "Acme Project",
        "risk_rating": "At Risk",
        "forecast_date": "2026-12-01",
        "budget": 100000,
    }]
    assert result["matched_dashboard_records"] == result["dashboard_rows"]
    assert result["final_report"]["primary_kpi"] is not None
    assert result["final_report"]["primary_risk"]["name"] in (
        result["final_report"]["markdown_report"]
    )
    assert result["final_report"]["markdown_report"].count(
        result["final_report"]["business_query"]
    ) == 1
    assert "## Executive Summary" in result["final_report"]["markdown_report"]
    assert "## Executive Decision Required" in result["final_report"]["markdown_report"]
    assert "## Recommended Actions" in result["final_report"]["markdown_report"]
    assert "Top KPI Insights" not in result["final_report"]["markdown_report"]
    assert "Top Risks" not in result["final_report"]["markdown_report"]
    assert "Top Actions" not in result["final_report"]["markdown_report"]
    assert "Dashboard Records Evaluated:" not in result["final_report"]["markdown_report"]
    assert "strategy" not in result, "legacy strategy selector is not in the primary workflow"
    assert "compiled_rules" not in result, "legacy rule compilation is not in the primary workflow"
    assert "explanation" in result, "explanation must be present in workflow output"
    print("Scenario:", result.get("scenario"))
    print("Explanation:", result.get("explanation"))
    print("All assertions passed successfully!")


if __name__ == "__main__":
    asyncio.run(test_full_simulation_workflow())
