import logging
import json
from typing import Any, Dict, List, Optional, Tuple
import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)

_SENSITIVE_HEADER_NAMES = {"authorization", "cookie", "set-cookie"}
_SENSITIVE_BODY_KEYS = {
    "authorization",
    "access_token",
    "token",
    "cookie",
    "password",
    "secret",
    "api_key",
}


def _is_sensitive_name(name: str) -> bool:
    normalized_name = name.lower()
    return (
        normalized_name in _SENSITIVE_HEADER_NAMES
        or any(
            marker in normalized_name
            for marker in ("token", "secret", "password", "api-key", "api_key")
        )
    )


def _sanitize_diagnostic_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): (
                "******"
                if str(key).lower() in _SENSITIVE_BODY_KEYS
                or _is_sensitive_name(str(key))
                else _sanitize_diagnostic_value(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize_diagnostic_value(item) for item in value]
    return value


def compare_headers(
    headers: Dict[str, str],
    reference_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Compare outgoing headers while ensuring credentials never enter logs."""
    outgoing = {key.lower(): (key, value) for key, value in headers.items()}
    reference = {
        key.lower(): (key, value)
        for key, value in (reference_headers or {}).items()
    }
    header_names = sorted(headers, key=str.lower)
    logger.debug("[BaseClient] Full outgoing header names: %s", header_names)

    important_headers = {
        "authorization",
        "x-enterprise-id",
        "x-domain-id",
        "cookie",
        "origin",
        "referer",
        "user-agent",
        "accept",
        "x-scope-id",
        "x-session-id",
    }
    comparison: Dict[str, Any] = {}
    for normalized_name in sorted(important_headers | set(outgoing) | set(reference)):
        sent = outgoing.get(normalized_name)
        expected = reference.get(normalized_name)
        header_name = sent[0] if sent else expected[0] if expected else normalized_name
        sent_value = sent[1] if sent else None
        expected_value = expected[1] if expected else None
        sensitive = _is_sensitive_name(normalized_name)
        comparison[header_name] = {
            "outgoing": "******" if sensitive and sent else sent_value,
            "reference": "******" if sensitive and expected else expected_value,
        }
        logger.debug(
            "[BaseClient] Header %s=%s",
            header_name,
            comparison[header_name]["outgoing"],
        )
        if reference_headers is not None:
            equal = sent_value is not None and sent_value == expected_value
            logger.info(
                "[BaseClient] Header comparison %s: %s",
                header_name,
                "MATCH" if equal else "DIFFERENT OR MISSING",
            )
    return comparison


class BaseClient:
    """
    Enterprise-ready asynchronous HTTP client base class.
    Enforces centralized JWT Bearer authentication, tenant scope headers,
    timeouts, structured request/response logging, and robust error handling.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        default_headers: Optional[Dict[str, str]] = None,
        auth_token: Optional[str] = None,
        scope_id: Optional[str] = None,
        scope_header_name: Optional[str] = None,
        enterprise_id: Optional[str] = None,
        domain_ids: Optional[List[str]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_headers = default_headers or {}
        self.auth_token = auth_token
        self.scope_id = scope_id
        self.enterprise_id = enterprise_id
        self.domain_ids = domain_ids
        self.scope_header_name = scope_header_name or settings.ARIIA_SCOPE_HEADER_NAME or "X-Scope-Id"

    def _build_url(self, endpoint: str) -> str:
        """
        Construct full request URL ensuring proper path formatting and eliminating
        redundant /api/v1 prefixes if present in both base_url and endpoint.
        """
        clean_base = self.base_url.rstrip("/")
        clean_endpoint = endpoint.lstrip("/")

        # Prevent duplicate /api/v1/api/v1 paths
        if clean_base.endswith("/api/v1") and clean_endpoint.startswith("api/v1/"):
            clean_endpoint = clean_endpoint[len("api/v1/"):]
        elif clean_base.endswith("/api/v1") and clean_endpoint == "api/v1":
            clean_endpoint = ""

        if clean_endpoint:
            return f"{clean_base}/{clean_endpoint}"
        return clean_base
    
    def _get_headers(
        self,
        request_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Build unified request headers with:

        - Authorization Bearer token
        - Enterprise context
        - Domain context
        - Optional scope context
        """

        headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "ARIIA-Simulation-Agent/1.0",
        }

        headers.update(self.default_headers)

        # ------------------------------------------
        # Authorization
        # ------------------------------------------

        effective_token = (
            self.auth_token
            or settings.access_token
        )

        if effective_token:

            token = effective_token.strip()

            if token.lower().startswith("bearer "):
                token = token[7:].strip()

            headers["Authorization"] = (
                f"Bearer {token}"
            )

        # ------------------------------------------
        # Enterprise Context
        # ------------------------------------------

        effective_enterprise = (
            self.enterprise_id
            or settings.enterprise_id
        )

        if effective_enterprise:

            headers[
                "X-Enterprise-Id"
            ] = effective_enterprise.strip()

        # ------------------------------------------
        # Domain Context
        # ------------------------------------------

        effective_domains = (
            self.domain_ids
            or settings.domain_ids
        )

        if effective_domains:

            headers[
                "X-Domain-Id"
            ] = ",".join(domain.strip() for domain in effective_domains if domain.strip())

        # ------------------------------------------
        # Scope Context
        # Kept only for compatibility
        # ------------------------------------------

        effective_scope = (
            self.scope_id
            or settings.scope_id
        )

        if (
            effective_scope
            and self.scope_header_name
        ):
            headers[
                self.scope_header_name
            ] = effective_scope.strip()

        if settings.ARIIA_COOKIE:
            headers["Cookie"] = settings.ARIIA_COOKIE.strip()

        if settings.ARIIA_SESSION_ID:
            headers["X-Session-Id"] = settings.ARIIA_SESSION_ID.strip()

        # ------------------------------------------
        # Request-specific Overrides
        # ------------------------------------------

        if request_headers:
            headers.update(request_headers)

        authorization = headers.get("Authorization", "")
        token = authorization
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        masked_token = "*" * min(len(token), 50)
        if len(token) > 50:
            masked_token += "..."

        logger.info(
            "[BaseClient] Context => "
            f"Enterprise={headers.get('X-Enterprise-Id')} "
            f"Domain={headers.get('X-Domain-Id')} "
            f"Scope={headers.get('X-Scope-Id')}"
        )

        logger.debug(
            "[BaseClient] Authorization token (masked, first 50 chars)="
            f"Bearer {masked_token}"
        )

        compare_headers(headers)

        return headers
    
    @staticmethod
    def _mask_headers(headers: Dict[str, str]) -> Dict[str, str]:
        """Mask sensitive authentication credentials for secure logging."""
        masked = dict(headers)
        for key in list(masked.keys()):
            if key.lower() in _SENSITIVE_HEADER_NAMES:
                masked[key] = "Bearer *****"
        return masked

    @staticmethod
    def _log_request(
        method: str,
        url: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Any] = None,
    ) -> None:
        logger.info("[BaseClient] Request %s %s", method.upper(), url)
        compare_headers(headers)
        if params:
            logger.debug(
                "[BaseClient] Request params: %s",
                json.dumps(_sanitize_diagnostic_value(params), default=str),
            )
        if body is not None:
            logger.debug(
                "[BaseClient] Request body: %s",
                json.dumps(_sanitize_diagnostic_value(body), default=str),
            )

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        Execute an authenticated asynchronous GET request and return the parsed JSON response.
        """
        url = self._build_url(endpoint)
        full_headers = self._get_headers(headers)
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}

        self._log_request("GET", url, full_headers, params=clean_params)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    params=clean_params,
                    headers=full_headers,
                )
                logger.info(f"[BaseClient] Response:\n{response.status_code} {response.reason_phrase}")
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as exc:
            logger.error(
                f"[BaseClient] HTTP status error for GET {url}: "
                f"{exc.response.status_code} - {exc.response.text}"
            )
            raise
        except httpx.TimeoutException as exc:
            logger.error(f"[BaseClient] Request timeout for GET {url}: {exc}")
            raise
        except httpx.RequestError as exc:
            logger.error(f"[BaseClient] Network/transport error for GET {url}: {exc}")
            raise
        except Exception as exc:
            logger.error(f"[BaseClient] Unexpected error during GET {url}: {exc}")
            raise

    async def get_with_status(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Any]:
        """
        Execute authenticated GET request and return a tuple of (status_code, parsed_json_or_text).
        Does not raise HTTPStatusError; useful for health-checks and diagnostic testing.
        """
        url = self._build_url(endpoint)
        full_headers = self._get_headers(headers)
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}

        self._log_request("GET", url, full_headers, params=clean_params)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    params=clean_params,
                    headers=full_headers,
                )
                logger.info(f"[BaseClient] Response:\n{response.status_code} {response.reason_phrase}")
                try:
                    data = response.json()
                except Exception:
                    data = response.text
                return response.status_code, data
        except Exception as exc:
            logger.error(f"[BaseClient] get_with_status failed for {url}: {exc}")
            raise

    async def post(
        self,
        endpoint: str,
        json_data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        Execute an authenticated asynchronous POST request and return the parsed JSON response.
        """
        url = self._build_url(endpoint)
        full_headers = self._get_headers(headers)
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}

        self._log_request(
            "POST", url, full_headers, params=clean_params, body=json_data
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=json_data,
                    params=clean_params,
                    headers=full_headers,
                )
                logger.info(f"[BaseClient] Response:\n{response.status_code} {response.reason_phrase}")
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as exc:
            logger.error(
                f"[BaseClient] HTTP status error for POST {url}: "
                f"{exc.response.status_code} - {exc.response.text}"
            )
            raise
        except httpx.TimeoutException as exc:
            logger.error(f"[BaseClient] Request timeout for POST {url}: {exc}")
            raise
        except httpx.RequestError as exc:
            logger.error(f"[BaseClient] Network/transport error for POST {url}: {exc}")
            raise
        except Exception as exc:
            logger.error(f"[BaseClient] Unexpected error during POST {url}: {exc}")
            raise

    async def post_with_status(
        self,
        endpoint: str,
        json_data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Any]:
        """
        Execute authenticated POST request and return a tuple of (status_code, parsed_json_or_text).
        """
        url = self._build_url(endpoint)
        full_headers = self._get_headers(headers)
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}

        self._log_request(
            "POST", url, full_headers, params=clean_params, body=json_data
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=json_data,
                    params=clean_params,
                    headers=full_headers,
                )
                logger.info(f"[BaseClient] Response:\n{response.status_code} {response.reason_phrase}")
                try:
                    data = response.json()
                except Exception:
                    data = response.text
                return response.status_code, data
        except Exception as exc:
            logger.error(f"[BaseClient] post_with_status failed for {url}: {exc}")
            raise