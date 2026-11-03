import asyncio
import pytest
from app.clients.procurement_client import ProcurementClient


@pytest.mark.asyncio
async def test_procurement_connectivity():
    client = ProcurementClient()
    print("\n================== Testing Procurement Service ==================")
    print(f"Target Base URL: {client.base_url}")

    # 1. Purchase orders list
    status, response = await client.get_with_status("/api/v1/procurement/purchase-orders", params={"limit": 5})
    print(f"GET /api/v1/procurement/purchase-orders -> HTTP {status}")
    print(f"Response: {str(response)[:300]}...")
    assert status < 500, f"Expected successful HTTP status code (<500), got {status}"

    # 2. Procurement stats
    status_stats, response_stats = await client.get_with_status("/api/v1/procurement/stats")
    print(f"GET /api/v1/procurement/stats -> HTTP {status_stats}")
    print(f"Response: {str(response_stats)[:300]}...")
    assert status_stats < 500, f"Expected successful HTTP status code (<500), got {status_stats}"


if __name__ == "__main__":
    asyncio.run(test_procurement_connectivity())
