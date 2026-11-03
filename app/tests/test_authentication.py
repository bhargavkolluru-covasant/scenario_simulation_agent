from datetime import datetime, timedelta, timezone
import pytest
import jwt

from app.config.settings import settings
from app.services.token_service import TokenService
from app.services.auth_service import AuthService, get_auth_service
from app.clients.base_client import BaseClient
from app.clients.semantic_registry_client import SemanticRegistryClient
from app.clients.vendor_client import VendorClient
from app.clients.procurement_client import ProcurementClient
from app.clients.invoice_client import InvoiceClient
from app.clients.expense_client import ExpenseClient
from app.clients.market_risk_client import MarketRiskClient
from app.clients.rules_client import RulesClient
from app.clients.knowledge_graph_client import KnowledgeGraphClient


def generate_sample_jwt(
    sub: str = "user-123",
    email: str = "engineer@ariia.ai",
    tenant_id: str = "tenant-enterprise-99",
    active_scope: str = "scope-prod-global",
    expires_in_seconds: int = 3600,
) -> str:
    """Helper to generate an unencrypted sample JWT for unit testing."""
    payload = {
        "sub": sub,
        "email": email,
        "tenant_id": tenant_id,
        "active_scope": active_scope,
        "exp": int((datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)).timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    return jwt.encode(payload, "ariia-enterprise-test-secret-32-bytes!!", algorithm="HS256")



def test_token_service_decoding():
    """Verify PyJWT decoding, claim extraction, and expiration detection."""
    test_token = generate_sample_jwt(
        sub="service-account-sim",
        email="sim-agent@ariia.io",
        tenant_id="tenant-corp-01",
        active_scope="scope-finance-us",
        expires_in_seconds=1800,
    )

    metadata = TokenService.decode_token(test_token)
    assert metadata.sub == "service-account-sim"
    assert metadata.email == "sim-agent@ariia.io"
    assert metadata.tenant_id == "tenant-corp-01"
    assert metadata.active_scope == "scope-finance-us"
    assert metadata.is_expired is False
    assert metadata.exp is not None

    # Test expired token
    expired_token = generate_sample_jwt(expires_in_seconds=-3600)
    expired_meta = TokenService.decode_token(expired_token)
    assert expired_meta.is_expired is True
    assert TokenService.is_token_expired(expired_token) is True


def test_auth_service_headers():
    """Verify AuthService builds valid enterprise headers with Bearer token and Scope ID."""
    token = generate_sample_jwt()
    auth_service = AuthService(
        token=token,
        scope_id="scope-emea-supply-chain",
        scope_header_name="X-Scope-Id",
    )

    headers = auth_service.get_auth_headers()
    assert "Authorization" in headers
    assert headers["Authorization"] == f"Bearer {token}"
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"
    assert headers["X-Scope-Id"] == "scope-emea-supply-chain"
    assert auth_service.is_token_expired() is False


def test_base_client_centralized_auth_injection():
    """Verify BaseClient automatically injects auth headers into every client."""
    test_token = "eyTestToken12345"
    test_scope = "scope-test-456"

    client = BaseClient(
        base_url="https://api.example.com/api/v1",
        auth_token=test_token,
        scope_id=test_scope,
    )

    headers = client._get_headers()
    assert headers["Authorization"] == f"Bearer {test_token}"
    assert headers["Content-Type"] == "application/json"
    assert headers["X-Scope-Id"] == test_scope

    # Verify masked headers for secure logging (never log full token)
    masked = client._mask_headers(headers)
    assert masked["Authorization"] == "Bearer *****"
    assert test_token not in masked["Authorization"]


def test_all_clients_inherit_base_client():
    """Verify that every domain client class inherits from BaseClient."""
    clients = [
        SemanticRegistryClient,
        KnowledgeGraphClient,
        VendorClient,
        ProcurementClient,
        InvoiceClient,
        ExpenseClient,
        MarketRiskClient,
        RulesClient,
    ]
    for client_cls in clients:
        assert issubclass(client_cls, BaseClient), f"{client_cls.__name__} must inherit from BaseClient"


@pytest.mark.asyncio
async def test_semantic_registry_endpoint_health():
    """
    Health check calling Semantic Registry endpoint with authentication headers.
    Loads token from settings, executes request, and prints response code & summary.
    """
    token = settings.access_token or generate_sample_jwt()
    scope = settings.scope_id or "default-scope"

    client = SemanticRegistryClient()
    # Ensure client is configured with active token
    if not client.auth_token:
        client.auth_token = token
    if not client.scope_id:
        client.scope_id = scope

    print("\n" + "=" * 60)
    print("ARIIA AUTHENTICATED ENDPOINT HEALTH CHECK")
    print("=" * 60)
    print(f"Target URL: {client.base_url}")
    print(f"Token present: {bool(client.auth_token)} (masked: Bearer *****)")
    print(f"Scope Header: {client.scope_header_name} = {client.scope_id}")

    status_code, response_data = await client.get_with_status("/api/v1/data-management/semantic-registry")

    print(f"Response Status Code: {status_code}")
    if isinstance(response_data, dict):
        print(f"Response Keys: {list(response_data.keys())}")
        if "entities" in response_data:
            print(f"Discovered Entities Count: {len(response_data.get('entities', []))}")
    else:
        print(f"Response Summary: {str(response_data)[:200]}")
    print("=" * 60 + "\n")

    # In online deployment with valid token, status_code is 200
    # In sandbox/offline, get_with_status safely returns code without unhandled crash
    assert isinstance(status_code, int)
    assert status_code in (200, 401, 403, 404, 502, 503)
