import asyncio
import pytest
from app.clients.semantic_registry_client import SemanticRegistryClient


@pytest.mark.asyncio
async def test_semantic_registry_connectivity():
    client = SemanticRegistryClient()
    print("\n================== Testing Semantic Registry ==================")
    print(f"Target Base URL: {client.base_url}")

    # 1. Full Registry
    status, response = await client.get_with_status("/api/v1/data-management/semantic-registry")
    print(f"GET /api/v1/data-management/semantic-registry -> HTTP {status}")
    print(f"Response: {str(response)[:300]}...")
    assert status < 500, f"Expected successful HTTP status code (<500), got {status}"

    # 2. Entities List
    status_entities, response_entities = await client.get_with_status("/api/v1/data-management/semantic-registry/entities")
    print(f"GET /api/v1/data-management/semantic-registry/entities -> HTTP {status_entities}")
    print(f"Response: {str(response_entities)[:300]}...")
    assert status_entities < 500, f"Expected successful HTTP status code (<500), got {status_entities}"


if __name__ == "__main__":
    asyncio.run(test_semantic_registry_connectivity())
