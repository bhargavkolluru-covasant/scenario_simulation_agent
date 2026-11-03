import pytest

from app.services.knowledge_graph_service import KnowledgeGraphService
from app.tests.kg_validation_support import configured_node_id, live_kg_client


@pytest.mark.asyncio
async def test_knowledge_graph_subgraph() -> None:
    client = live_kg_client()
    node_id = configured_node_id()
    if node_id is None:
        nodes = KnowledgeGraphService.normalize_graph(
            await client.get_graph()
        )["nodes"]
        node_id = next(
            (
                str(node[key])
                for node in nodes
                if isinstance(node, dict)
                for key in ("id", "node_id", "uuid", "key")
                if node.get(key) is not None
            ),
            None,
        )
    if node_id is None:
        pytest.skip(
            "Graph has no node ID; set KG_NODE_ID to test the subgraph endpoint."
        )

    payload = await client.get_subgraph(node_id)
    print(f"Node ID: {node_id}")
    print(f"Subgraph Response: {payload}")
    assert payload is not None
