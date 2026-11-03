import pytest

from app.clients.base_client import BaseClient
from app.clients.knowledge_graph_client import KnowledgeGraphClient


@pytest.mark.asyncio
async def test_knowledge_graph_client_uses_expected_endpoints(monkeypatch) -> None:
    calls = []

    async def fake_get(self, endpoint, params=None, headers=None):
        calls.append((endpoint, params))
        return {"ok": True}

    monkeypatch.setattr(BaseClient, "get", fake_get)
    client = KnowledgeGraphClient(base_url="https://platform.example")

    assert await client.get_graph() == {"ok": True}
    assert await client.get_stats() == {"ok": True}
    assert await client.get_node("vendor/one") == {"ok": True}
    assert await client.get_entities("vendor type") == {"ok": True}
    assert await client.get_subgraph("vendor/one") == {"ok": True}
    assert calls == [
        (
            "/api/v1/data-management/knowledge-graph",
            {
                "node_type": None,
                "relationship_type": None,
                "limit": 100,
                "include_stats": True,
                "tier": "tables",
            },
        ),
        ("/api/v1/data-management/knowledge-graph/stats", None),
        ("/api/v1/data-management/knowledge-graph/node/vendor%2Fone", {"depth": 1}),
        (
            "/api/v1/data-management/knowledge-graph/entities/vendor%20type",
            {"limit": 1000},
        ),
        (
            "/api/v1/data-management/knowledge-graph/subgraph/vendor%2Fone",
            {"limit": 50},
        ),
    ]


@pytest.mark.asyncio
async def test_knowledge_graph_client_rejects_empty_path_parameters() -> None:
    client = KnowledgeGraphClient(base_url="https://platform.example")

    with pytest.raises(ValueError, match="node_id"):
        await client.get_node(" ")
    with pytest.raises(ValueError, match="node_type"):
        await client.get_entities("")
    with pytest.raises(ValueError, match="node_id"):
        await client.get_subgraph("")
