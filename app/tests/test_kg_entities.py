import pytest

from app.services.knowledge_graph_service import KnowledgeGraphService
from app.tests.kg_validation_support import configured_node_type, live_kg_client


@pytest.mark.asyncio
async def test_knowledge_graph_entities() -> None:
    client = live_kg_client()
    node_type = configured_node_type()
    if node_type is None:
        graph = await client.get_graph()
        summary = await KnowledgeGraphService(client).graph_summary(graph)
        node_type = next(iter(summary["node_types"]), None)
    if node_type is None:
        pytest.skip(
            "Graph has no discoverable node types; set KG_NODE_TYPE to test entities."
        )

    payload = await client.get_entities(node_type)
    print(f"Node Type: {node_type}")
    print(f"Entities Response: {payload}")
    assert payload is not None
