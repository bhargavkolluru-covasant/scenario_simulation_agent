import asyncio
import pytest
from app.clients.expense_client import ExpenseClient


@pytest.mark.asyncio
async def test_expense_connectivity():
    client = ExpenseClient()
    print("\n================== Testing Expense Service ==================")
    print(f"Target Base URL: {client.base_url}")

    # 1. Expenses list
    status, response = await client.get_with_status("/api/v1/expenses", params={"page": 1, "page_size": 5})
    print(f"GET /api/v1/expenses -> HTTP {status}")
    print(f"Response: {str(response)[:300]}...")
    assert status < 500, f"Expected successful HTTP status code (<500), got {status}"

    # 2. Expense stats
    status_stats, response_stats = await client.get_with_status("/api/v1/expenses/stats")
    print(f"GET /api/v1/expenses/stats -> HTTP {status_stats}")
    print(f"Response: {str(response_stats)[:300]}...")
    assert status_stats < 500, f"Expected successful HTTP status code (<500), got {status_stats}"


if __name__ == "__main__":
    asyncio.run(test_expense_connectivity())
