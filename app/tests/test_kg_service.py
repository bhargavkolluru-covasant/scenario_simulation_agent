import pytest

from app.clients.knowledge_graph_client import KnowledgeGraphClient
from app.services.knowledge_graph_service import KnowledgeGraphService


@pytest.mark.asyncio
async def test_graph_summary_normalizes_envelope_and_checks_connectivity() -> None:
    payload = {
        "data": {
            "graph": {
                "nodes": [
                    {"id": "vendor-1", "node_type": "vendor"},
                    {"id": "site-1", "type": "site"},
                    {"id": "unlinked", "type": "invoice"},
                ],
                "edges": [
                    {
                        "source": "vendor-1",
                        "target": "site-1",
                        "relationship_type": "SUPPLIES",
                    }
                ],
            }
        }
    }

    summary = await KnowledgeGraphService().graph_summary(payload)

    assert summary == {
        "graph_exists": True,
        "total_nodes": 3,
        "total_edges": 1,
        "node_types": {"invoice": 1, "site": 1, "vendor": 1},
        "relationship_types": {"SUPPLIES": 1},
        "impact_propagation_candidate_types": ["site", "vendor"],
        "usable_for_simulation": True,
        "explanation": (
            "The graph contains nodes and relationships whose endpoints resolve to "
            "known nodes, so it can support relationship-based impact propagation. "
            "Business relevance and data freshness still need domain validation."
        ),
    }


@pytest.mark.asyncio
async def test_graph_summary_marks_nodes_without_edges_unusable() -> None:
    summary = await KnowledgeGraphService().graph_summary(
        {"nodes": [{"id": "vendor-1", "node_type": "vendor"}], "edges": []}
    )

    assert summary["graph_exists"] is True
    assert summary["usable_for_simulation"] is False
    assert summary["explanation"] == (
        "The graph has nodes but no relationships to propagate impact."
    )


@pytest.mark.asyncio
async def test_graph_summary_fetches_graph_when_payload_is_omitted(monkeypatch) -> None:
    client = KnowledgeGraphClient(base_url="https://platform.example")

    async def fake_get_graph():
        return {"nodes": [], "edges": []}

    monkeypatch.setattr(client, "get_graph", fake_get_graph)
    summary = await KnowledgeGraphService(client=client).graph_summary()

    assert summary["graph_exists"] is False
    assert summary["total_nodes"] == 0
    assert summary["total_edges"] == 0
    assert summary["usable_for_simulation"] is False


@pytest.mark.asyncio
async def test_graph_summary_uses_full_counts_from_stats() -> None:
    summary = await KnowledgeGraphService().graph_summary(
        {
            "nodes": [{"id": "vendor-1", "node_type": "vendor"}],
            "edges": [],
        },
        stats_response={
            "total_nodes": 140,
            "total_relationships": 220,
            "node_types": {"vendor": 120, "site": 20},
            "relationship_types": {"SUPPLIES": 220},
        },
    )

    assert summary["total_nodes"] == 140
    assert summary["total_edges"] == 220
    assert summary["node_types"] == {"site": 20, "vendor": 120}
    assert summary["relationship_types"] == {"SUPPLIES": 220}
    assert summary["usable_for_simulation"] is False


def test_graph_intelligence_resolves_propagates_and_builds_dependency_paths() -> None:
    graph = {
        "nodes": [
            {"id": "p1", "name": "Horizon Heights", "node_type": "project"},
            {"id": "c1", "name": "Package A", "node_type": "contract"},
            {"id": "v1", "name": "North Build", "node_type": "contractor"},
            {"id": "s1", "name": "Stone Supply", "node_type": "vendor"},
            {"id": "cu1", "name": "Home Buyers", "node_type": "customer"},
        ],
        "edges": [
            {"source": "p1", "target": "c1", "relationship_type": "HAS_CONTRACT"},
            {"source": "c1", "target": "v1", "relationship_type": "AWARDED_TO"},
            {"source": "v1", "target": "s1", "relationship_type": "DEPENDS_ON"},
            {"source": "p1", "target": "cu1", "relationship_type": "DELIVERS_TO"},
        ],
    }
    service = KnowledgeGraphService()

    resolved = service.resolve_entity(graph, "horizon heights")
    assert resolved is not None
    assert resolved["resolved_node_id"] == "p1"
    assert resolved["match_type"] == "exact"

    related = service.find_related_entities(graph, "p1", max_depth=3)
    assert {entity["name"] for entity in related} == {
        "Package A",
        "North Build",
        "Stone Supply",
        "Home Buyers",
    }
    assert {entity["node_type"] for entity in related} == {
        "contract",
        "contractor",
        "vendor",
        "customer",
    }

    paths = service.compute_dependency_chain(graph, "p1", max_depth=3)
    assert any(
        path["entities"] == ["Horizon Heights", "Package A", "North Build", "Stone Supply"]
        for path in paths
    )
    blast_radius = service.compute_blast_radius(graph, "p1", max_depth=3)
    assert blast_radius["affected_entity_count"] == 4
    assert blast_radius["affected_entities_by_type"]["vendor"] == 1


def test_graph_root_cause_candidates_require_linked_business_evidence() -> None:
    graph = {
        "nodes": [
            {"id": "p1", "name": "Horizon Heights", "node_type": "project"},
            {"id": "c1", "name": "Package A", "node_type": "contract"},
        ],
        "edges": [
            {"source": "p1", "target": "c1", "relationship_type": "HAS_CONTRACT"}
        ],
    }
    candidates = KnowledgeGraphService().find_root_cause_candidates(
        graph,
        "Horizon Heights",
        rules=[{
            "name": "Handover delay threshold",
            "target_entity": "Horizon Heights",
            "severity": "HIGH",
        }],
        matched_dashboard_records=[{
            "project": "Horizon Heights",
            "status": "Handover delayed",
        }],
        kpi_insights={"kpis": [{
            "name": "Handover delay",
            "reasoning": "Horizon Heights handover is delayed.",
        }]},
    )

    assert {item["evidence_type"] for item in candidates} == {
        "business_rule",
        "dashboard_record",
        "kpi_insight",
    }
    assert all(item["causality_confirmed"] is False for item in candidates)
