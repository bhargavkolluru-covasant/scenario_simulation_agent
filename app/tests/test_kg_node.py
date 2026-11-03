from typing import Optional

import pytest

from app.services.knowledge_graph_service import KnowledgeGraphService
from app.tests.kg_validation_support import configured_node_id, live_kg_client


def _first_node_id(graph_response) -> Optional[str]:
    nodes = KnowledgeGraphService.normalize_graph(graph_response)["nodes"]
    for node in nodes:
        if isinstance(node, dict):
            for key in ("id", "node_id", "uuid", "key"):
                if node.get(key) is not None:
                    return str(node[key])
    return None


@pytest.mark.asyncio
async def test_knowledge_graph_node() -> None:
    client = live_kg_client()
    node_id = configured_node_id()
    if node_id is None:
        node_id = _first_node_id(await client.get_graph())
    if node_id is None:
        pytest.skip("Graph has no node ID; set KG_NODE_ID to test the node endpoint.")

    payload = await client.get_node(node_id)
    print(f"Node ID: {node_id}")
    print(f"Node Response: {payload}")
    assert payload is not None
