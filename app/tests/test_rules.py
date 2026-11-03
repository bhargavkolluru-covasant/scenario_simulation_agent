import asyncio
import pytest
from app.clients.rules_client import RulesClient


@pytest.mark.asyncio
async def test_rules_connectivity():
    client = RulesClient()
    print("\n================== Testing Rules Service ==================")
    print(f"Target Base URL: {client.base_url}")

    # 1. Rules list
    status, response = await client.get_with_status("/api/v1/rules", params={"limit": 5})
    print(f"GET /api/v1/rules -> HTTP {status}")
    print(f"Response: {str(response)[:300]}...")
    assert status < 500, f"Expected successful HTTP status code (<500), got {status}"

    # 2. If rules exist, test single rule detail / explain
    rule_id = None
    if isinstance(response, dict) and "rules" in response and response["rules"]:
        first_rule = response["rules"][0]
        rule_id = first_rule.get("rule_id")

    if rule_id:
        status_rule, response_rule = await client.get_with_status(f"/api/v1/rules/{rule_id}")
        print(f"GET /api/v1/rules/{rule_id} -> HTTP {status_rule}")
        print(f"Response: {str(response_rule)[:300]}...")
        assert status_rule < 500


if __name__ == "__main__":
    asyncio.run(test_rules_connectivity())
