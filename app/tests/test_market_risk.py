import asyncio
import pytest
from app.clients.market_risk_client import MarketRiskClient


@pytest.mark.asyncio
async def test_market_risk_connectivity():
    client = MarketRiskClient()
    print("\n================== Testing Market Risk Service ==================")
    print(f"Target Base URL: {client.base_url}")

    # 1. FX exposure
    status, response = await client.get_with_status("/api/v1/market-risk/fx-exposure", params={"limit": 5})
    print(f"GET /api/v1/market-risk/fx-exposure -> HTTP {status}")
    print(f"Response: {str(response)[:300]}...")
    assert status < 500, f"Expected successful HTTP status code (<500), got {status}"

    # 2. Currency risk score
    status_score, response_score = await client.get_with_status("/api/v1/market-risk/currency-risk-score")
    print(f"GET /api/v1/market-risk/currency-risk-score -> HTTP {status_score}")
    print(f"Response: {str(response_score)[:300]}...")
    assert status_score < 500, f"Expected successful HTTP status code (<500), got {status_score}"

    # 3. Risk distribution
    status_dist, response_dist = await client.get_with_status("/api/v1/market-risk/risk-distribution")
    print(f"GET /api/v1/market-risk/risk-distribution -> HTTP {status_dist}")
    print(f"Response: {str(response_dist)[:300]}...")
    assert status_dist < 500, f"Expected successful HTTP status code (<500), got {status_dist}"


if __name__ == "__main__":
    asyncio.run(test_market_risk_connectivity())
