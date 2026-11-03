import json
import logging
import os

import httpx
import pytest

from app.clients.base_client import BaseClient, compare_headers
from app.config.settings import settings
from app.tests.test_dashboard_manual import URL, _safe_headers
from app.tests.test_token_diagnostics import token_diagnostics


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("RUN_ARIIA_MANUAL_TEST") != "1",
    reason="Set RUN_ARIIA_MANUAL_TEST=1 to send a live ARIIA request.",
)
async def test_postman_equivalence_request() -> None:
    client = BaseClient(base_url=settings.PLATFORM_BACKEND_URL)
    generated_headers = client._get_headers()
    headers = {
        name: generated_headers[name]
        for name in ("Authorization", "X-Enterprise-Id", "X-Domain-Id")
    }
    url = client._build_url(
        "/api/v1/dashboards/dash_3e633ae526ae/data"
    )

    print("Constructed request:", json.dumps({"method": "GET", "url": url}, indent=2))
    print("All outgoing headers:", json.dumps(_safe_headers(headers), indent=2))
    print(
        "Safe token metadata:",
        json.dumps(token_diagnostics(settings.access_token), indent=2),
    )
    compare_headers(generated_headers, headers)

    async with httpx.AsyncClient(timeout=settings.API_TIMEOUT) as http_client:
        response = await http_client.get(url, headers=headers)

    print("Status:", response.status_code)
    try:
        print("Response body:", json.dumps(response.json(), indent=2))
    except ValueError:
        print("Response body:", response.text)
    assert response.status_code == 200


def test_header_comparison_redacts_credentials() -> None:
    result = compare_headers(
        {
            "Authorization": "Bearer python-test-token",
            "X-Enterprise-Id": "enterprise-a",
            "Cookie": "session=private",
        },
        {
            "Authorization": "Bearer postman-test-token",
            "X-Enterprise-Id": "enterprise-a",
            "Cookie": "session=other-private",
        },
    )
    assert result["Authorization"] == {
        "outgoing": "******",
        "reference": "******",
    }
    assert result["Cookie"] == {
        "outgoing": "******",
        "reference": "******",
    }


def test_cookie_and_session_headers_are_opt_in(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ARIIA_COOKIE", "test-cookie")
    monkeypatch.setattr(settings, "ARIIA_SESSION_ID", "test-session-id")

    headers = BaseClient(base_url=settings.PLATFORM_BACKEND_URL)._get_headers()

    assert headers["Cookie"] == "test-cookie"
    assert headers["X-Session-Id"] == "test-session-id"


def test_request_debugging_masks_credentials_and_sensitive_body(caplog) -> None:
    caplog.set_level(logging.DEBUG)
    BaseClient._log_request(
        "POST",
        "https://platform.example/api/test",
        {
            "Authorization": "Bearer request-secret",
            "Cookie": "cookie-secret",
            "X-Enterprise-Id": "enterprise-a",
        },
        body={
            "name": "sample",
            "access_token": "body-secret",
        },
    )

    log_output = caplog.text
    assert "POST https://platform.example/api/test" in log_output
    assert "Authorization" in log_output
    assert "X-Enterprise-Id" in log_output
    assert "request-secret" not in log_output
    assert "cookie-secret" not in log_output
    assert "body-secret" not in log_output
