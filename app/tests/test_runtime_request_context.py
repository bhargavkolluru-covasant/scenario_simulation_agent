import pytest

from app.api import routes
from app.clients.dashboard_client import DashboardClient


@pytest.mark.asyncio
async def test_simulation_request_context_is_used_for_workflow(monkeypatch):
    received_state = {}

    async def fake_ainvoke(state):
        received_state.update(state)
        return {
            **state,
            "final_report": {},
            "status": "COMPLETED",
        }

    monkeypatch.setattr(routes.workflow, "ainvoke", fake_ainvoke)
    request = routes.SimulationRequest(
        query="What if Horizon Heights handover is delayed by 90 days?",
        dashboard_id="dash-request",
        enterprise_id="ent-request",
        domain_ids=["domain-one", "domain-two"],
        scope_id="scope-request",
        access_token="Bearer request-token",
    )

    response = await routes.run_simulation(
        request,
        include_full_state=True,
    )

    assert received_state["access_token"] == "Bearer request-token"
    assert received_state["dashboard_id"] == "dash-request"
    assert received_state["enterprise_id"] == "ent-request"
    assert received_state["domain_ids"] == ["domain-one", "domain-two"]
    assert "domain_id" not in received_state
    assert received_state["scope_id"] == "scope-request"
    assert received_state["include_full_state"] is True
    assert response["state"]["access_token"] == "******"

    headers = DashboardClient(
        auth_token=received_state["access_token"],
        enterprise_id=received_state["enterprise_id"],
        domain_ids=received_state["domain_ids"],
    )._get_headers()
    assert headers["Authorization"] == "Bearer request-token"
    assert headers["X-Enterprise-Id"] == "ent-request"
    assert headers["X-Domain-Id"] == "domain-one,domain-two"


def test_simulation_request_schema_includes_frontend_example():
    example = routes.SimulationRequest.model_json_schema()["example"]

    assert example == {
        "query": "What if Horizon Heights handover is delayed by 90 days?",
        "dashboard_id": "dash_3e633ae526ae",
        "enterprise_id": "ent_40cb7d18dca2",
        "domain_ids": ["re_core_master", "..."],
        "scope_id": "ec6bae6f...",
        "access_token": "Bearer token",
    }


def test_legacy_domain_id_request_is_normalized_to_domain_ids():
    request = routes.SimulationRequest(
        query="Run the scenario",
        domain_id="legacy-domain",
    )

    assert request.domain_ids == ["legacy-domain"]
    assert "domain_id" not in request.model_dump()
