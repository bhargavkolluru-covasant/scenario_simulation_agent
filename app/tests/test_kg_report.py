import json

import pytest

from app.services.knowledge_graph_service import KnowledgeGraphService
from app.tests.kg_validation_support import live_kg_client


@pytest.mark.asyncio
async def test_knowledge_graph_validation_report() -> None:
    client = live_kg_client()
    graph = await client.get_graph()
    stats = await client.get_stats()
    summary = await KnowledgeGraphService(client).graph_summary(
        graph,
        stats_response=stats,
    )
    report = {
        "graph_exists": summary["graph_exists"],
        "total_nodes": summary["total_nodes"],
        "total_edges": summary["total_edges"],
        "node_types": summary["node_types"],
        "relationship_types": summary["relationship_types"],
        "usable_for_simulation": summary["usable_for_simulation"],
        "impact_propagation_candidate_types": summary[
            "impact_propagation_candidate_types"
        ],
        "explanation": summary["explanation"],
        "stats_payload": stats,
    }

    print("Knowledge Graph Validation Report:")
    print(json.dumps(report, indent=2, default=str))
    assert report["graph_exists"] == bool(
        report["total_nodes"] or report["total_edges"]
    )
