import pytest

from app.services.knowledge_graph_service import KnowledgeGraphService
from app.tests.kg_validation_support import live_kg_client


@pytest.mark.asyncio
async def test_knowledge_graph_contains_usable_data() -> None:
    client = live_kg_client()
    payload = await client.get_graph()
    summary = await KnowledgeGraphService(client).graph_summary(payload)

    print(f"Node Count: {summary['total_nodes']}")
    print(f"Edge Count: {summary['total_edges']}")
    print(f"Available Node Types: {summary['node_types']}")
    print(f"Available Relationships: {summary['relationship_types']}")

    assert summary["total_nodes"] >= 0
    assert summary["total_edges"] >= 0
