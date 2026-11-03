import asyncio
import pytest
from app.clients.knowledge_graph_client import KnowledgeGraphClient


@pytest.mark.asyncio
async def test_knowledge_graph_connectivity():
    client = KnowledgeGraphClient()
    print("\n================== Testing Knowledge Graph ==================")
    print(f"Target Base URL: {client.base_url}")

    # 1. Knowledge Graph Top Level
    status, response = await client.get_with_status(
        "/api/v1/data-management/knowledge-graph",
        params={"limit": 10, "tier": "tables"},
    )
    print(f"GET /api/v1/data-management/knowledge-graph -> HTTP {status}")
    print(f"Response: {str(response)[:300]}...")
    assert status < 500, f"Expected successful HTTP status code (<500), got {status}"

    # 2. Knowledge Graph Stats
    status_stats, response_stats = await client.get_with_status("/api/v1/data-management/knowledge-graph/stats")
    print(f"GET /api/v1/data-management/knowledge-graph/stats -> HTTP {status_stats}")
    print(f"Response: {str(response_stats)[:300]}...")
    assert status_stats < 500, f"Expected successful HTTP status code (<500), got {status_stats}"


if __name__ == "__main__":
    asyncio.run(test_knowledge_graph_connectivity())
