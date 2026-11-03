import asyncio
import pytest
from app.clients.invoice_client import InvoiceClient


@pytest.mark.asyncio
async def test_invoice_connectivity():
    client = InvoiceClient()
    print("\n================== Testing Invoice Service ==================")
    print(f"Target Base URL: {client.base_url}")

    # 1. Invoices list
    status, response = await client.get_with_status("/api/v1/invoices", params={"limit": 5})
    print(f"GET /api/v1/invoices -> HTTP {status}")
    print(f"Response: {str(response)[:300]}...")
    assert status < 500, f"Expected successful HTTP status code (<500), got {status}"

    # 2. Invoice stats
    status_stats, response_stats = await client.get_with_status("/api/v1/invoices/stats")
    print(f"GET /api/v1/invoices/stats -> HTTP {status_stats}")
    print(f"Response: {str(response_stats)[:300]}...")
    assert status_stats < 500, f"Expected successful HTTP status code (<500), got {status_stats}"


if __name__ == "__main__":
    asyncio.run(test_invoice_connectivity())
