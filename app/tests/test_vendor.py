import asyncio
import pytest
from app.clients.vendor_client import VendorClient


@pytest.mark.asyncio
async def test_vendor_connectivity():
    client = VendorClient()
    print("\n================== Testing Vendor Service ==================")
    print(f"Target Base URL: {client.base_url}")

    # 1. List Vendors
    status, response = await client.get_with_status("/api/v1/vendors", params={"limit": 5})
    print(f"GET /api/v1/vendors -> HTTP {status}")
    print(f"Response: {str(response)[:300]}...")
    assert status < 500, f"Expected successful HTTP status code (<500), got {status}"

    # 2. If vendor exists, test single vendor detail or risk-score
    vendor_id = None
    if isinstance(response, dict) and "vendors" in response and response["vendors"]:
        first_vendor = response["vendors"][0]
        vendor_id = first_vendor.get("vendor_id")

    if vendor_id:
        status_detail, response_detail = await client.get_with_status(f"/api/v1/vendors/{vendor_id}/risk-score")
        print(f"GET /api/v1/vendors/{vendor_id}/risk-score -> HTTP {status_detail}")
        print(f"Response: {str(response_detail)[:300]}...")
        assert status_detail < 500


if __name__ == "__main__":
    asyncio.run(test_vendor_connectivity())
