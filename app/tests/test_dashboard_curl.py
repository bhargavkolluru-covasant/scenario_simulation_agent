from app.clients.base_client import BaseClient
from app.config.settings import settings


def build_dashboard_curl_command() -> str:
    """Build a PowerShell curl.exe command without embedding credentials."""
    client = BaseClient(base_url=settings.PLATFORM_BACKEND_URL)
    url = client._build_url("/api/v1/dashboards/dash_3e633ae526ae/data")
    headers = client._get_headers()

    curl_headers = []
    for name, value in headers.items():
        if name.lower() == "authorization":
            value = "Bearer $env:ARIIA_ACCESS_TOKEN"
        elif name.lower() == "cookie":
            value = "$env:ARIIA_COOKIE"
        elif name.lower() == "x-session-id":
            value = "$env:ARIIA_SESSION_ID"
        curl_headers.append(f'-H "{name}: {value}"')
    return f'curl.exe -X GET "{url}" ' + " ".join(curl_headers)


def test_print_dashboard_curl_command() -> None:
    command = build_dashboard_curl_command()
    print("PowerShell equivalent command (credentials use environment variables):")
    print(command)
    assert "dash_3e633ae526ae/data" in command
    assert "$env:ARIIA_ACCESS_TOKEN" in command
