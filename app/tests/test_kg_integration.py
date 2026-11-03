from unittest.mock import AsyncMock

import pytest

from app.clients.knowledge_graph_client import KnowledgeGraphClient
from app.nodes.knowledge_graph_node import knowledge_graph_node
from app.services.explainability_service import ExplainabilityService
from app.services.impact_analysis_service import ImpactAnalysisService
from app.services.report_service import ReportService
from app.services.simulation_service import SimulationService


@pytest.mark.asyncio
async def test_graph_intelligence_flows_into_simulation_impact_and_report(monkeypatch):
    graph = {
        "nodes": [
            {"id": "p1", "name": "Horizon Heights", "node_type": "project"},
            {"id": "c1", "name": "Contract Package A", "node_type": "contract"},
            {"id": "v1", "name": "North Build", "node_type": "contractor"},
            {"id": "cu1", "name": "Home Buyers", "node_type": "customer"},
        ],
        "edges": [
            {"source": "p1", "target": "c1", "relationship_type": "HAS_CONTRACT"},
            {"source": "c1", "target": "v1", "relationship_type": "AWARDED_TO"},
            {"source": "p1", "target": "cu1", "relationship_type": "DELIVERS_TO"},
        ],
        "stats": {},
    }
    monkeypatch.setattr(
        KnowledgeGraphClient,
        "get_knowledge_graph",
        AsyncMock(return_value=graph),
    )
    monkeypatch.setattr(
        KnowledgeGraphClient,
        "get_subgraph",
        AsyncMock(return_value=graph),
    )
    state = {
        "query": "What if Horizon Heights handover is delayed by 90 days?",
        "scenario": {"target_entity": "Horizon Heights", "change_percentage": 20},
        "entity_match_summary": {"target_entity": "Horizon Heights"},
        "matched_dashboard_records": [{
            "project": "Horizon Heights",
            "status": "Handover delay risk",
        }],
        "kpi_insights": {"kpis": [{
            "name": "Handover delay",
            "value": 1,
            "reasoning": "Horizon Heights handover is delayed.",
        }]},
        "rules": [{
            "name": "Handover delay threshold",
            "target_entity": "Horizon Heights",
            "severity": "HIGH",
        }],
        "actions": [],
        "dashboard_rows": [],
        "include_full_state": True,
    }

    await knowledge_graph_node(state)
    simulation = await SimulationService().run(state)
    state["simulation_result"] = simulation
    impact = await ImpactAnalysisService().analyze(state)
    state["impact_result"] = impact
    explanation = await ExplainabilityService(
        llm_service=type("UnconfiguredLLM", (), {"is_configured": False})()
    ).explain(state)
    state["explanation"] = explanation
    report = await ReportService().generate_report(state)

    assert state["graph_summary"]["usable_for_simulation"] is True
    assert "North Build" in {item["name"] for item in state["related_entities"]}
    assert simulation["knowledge_graph_context"]["dependency_paths"]
    assert impact["affected_entities"]
    assert impact["graph_influence_score"] > 0
    assert impact["relationship_risk_score"] > 0
    assert "Contract Package A" in explanation["operational_impact"]
    class CapturingLLM:
        is_configured = True
        prompt = ""

        async def generate_json(self, prompt, system_instruction):
            self.prompt = prompt
            return {}

    capturing_llm = CapturingLLM()
    await ExplainabilityService(llm_service=capturing_llm).explain(state)
    assert "Executive context:" in capturing_llm.prompt
    assert "Contract Package A" in capturing_llm.prompt
    assert "Handover delay threshold" in capturing_llm.prompt
    assert "## Knowledge Graph Findings" not in report["markdown_report"]
    assert "## Affected Entities" not in report["markdown_report"]
    assert "## Blast Radius Analysis" not in report["markdown_report"]
    assert "## Dependency Chains" not in report["markdown_report"]


@pytest.mark.asyncio
async def test_graph_unavailable_degrades_without_stopping_downstream(monkeypatch):
    monkeypatch.setattr(
        KnowledgeGraphClient,
        "get_knowledge_graph",
        AsyncMock(side_effect=RuntimeError("service unavailable")),
    )
    state = {
        "query": "Evaluate Horizon Heights",
        "scenario": {"target_entity": "Horizon Heights"},
        "entity_match_summary": {},
        "rules": [],
        "matched_dashboard_records": [],
        "kpi_insights": {},
        "actions": [],
    }

    await knowledge_graph_node(state)
    simulation = await SimulationService().run(state)
    state["simulation_result"] = simulation
    impact = await ImpactAnalysisService().analyze(state)

    assert state["graph_summary"]["usable_for_simulation"] is False
    assert state["graph_summary"]["explanation"].startswith("Graph unavailable")
    assert simulation["metrics"]["risk_score"] >= 0
    assert impact["overall_severity"]


@pytest.mark.asyncio
async def test_empty_graph_uses_explicit_fallback_without_stopping(monkeypatch):
    monkeypatch.setattr(
        KnowledgeGraphClient,
        "get_knowledge_graph",
        AsyncMock(return_value={"nodes": [], "edges": [], "stats": {}}),
    )
    state = {
        "query": "Evaluate Horizon Heights",
        "scenario": {"target_entity": "Horizon Heights"},
        "entity_match_summary": {},
        "rules": [],
        "matched_dashboard_records": [],
        "kpi_insights": {},
        "actions": [],
    }

    await knowledge_graph_node(state)
    simulation = await SimulationService().run(state)

    assert state["graph_summary"]["total_nodes"] == 0
    assert state["graph_summary"]["total_edges"] == 0
    assert state["graph_summary"]["explanation"].startswith(
        "Graph unavailable or no relationships found."
    )
    assert simulation["parameters"]["knowledge_graph_usable"] is False
