import os
from typing import Dict, Optional

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    # ==================================================
    # Core
    # ==================================================

    API_TIMEOUT: float = 30.0

    BASE_URL: str = (
        "https://ariia-data-ingestion-service-trg-273497745552.us-central1.run.app/api/v1"
    )

    PLATFORM_BACKEND_URL: str = (
        "https://ariia-platform-backend-trg-273497745552.us-central1.run.app"
    )

    # ==================================================
    # Dashboard / KPI Intelligence
    # ==================================================

    DASHBOARD_URL: Optional[str] = None

    KPI_INSIGHTS_URL: Optional[str] = None

    ACTIONS_URL: Optional[str] = None

    DASHBOARD_ID: Optional[str] = None

    # ==================================================
    # Context
    # ==================================================

    ARIIA_ENTERPRISE_ID: str = (
        "ent_40cb7d18dca2"
    )

    ARIIA_DOMAIN_IDS: str = (
        "re_core_master,re_documents_conversation_intelligence,"
        "re_finance_cost_performance,re_land_zoning_feasibility,"
        "re_market_external_intelligence,re_portfolio_operations,"
        "re_project_delivery_construction,re_sales_customer_channel"
    )

    ARIIA_COOKIE: Optional[str] = None

    ARIIA_SESSION_ID: Optional[str] = None

    # ==================================================
    # Platform Clients
    # ==================================================

    SEMANTIC_REGISTRY_URL: Optional[str] = None

    KNOWLEDGE_GRAPH_URL: Optional[str] = None

    RULES_SERVICE_URL: Optional[str] = None

    RULE_COMPILATION_URL: Optional[str] = None

    VENDOR_SERVICE_URL: Optional[str] = None

    PROCUREMENT_SERVICE_URL: Optional[str] = None

    INVOICE_SERVICE_URL: Optional[str] = None

    EXPENSE_SERVICE_URL: Optional[str] = None

    MARKET_RISK_SERVICE_URL: Optional[str] = None

    # ==================================================
    # Authentication
    # ==================================================

    ARIIA_ACCESS_TOKEN: Optional[str] = None

    ARIIA_SCOPE_ID: Optional[str] = None

    ARIIA_SCOPE_HEADER_NAME: str = (
        "X-Scope-Id"
    )

    # ==================================================
    # LLM
    # ==================================================

    LLM_PROVIDER: str = "groq"

    COPILOT_BASE_URL: str = "http://127.0.0.1:3030/v1"

    COPILOT_MODEL: str = "gpt-4o-copilot"

    COPILOT_TIMEOUT: float = 60.0

    COPILOT_MAX_RETRIES: int = 3
    GROQ_API_KEY: Optional[str] = None

    GROQ_MODEL: str = (
        "openai/gpt-oss-120b"
    )

    GROQ_TIMEOUT: float = 60.0

    GROQ_MAX_RETRIES: int = 3

    GEMINI_API_KEY: Optional[str] = None

    GEMINI_MODEL: str = (
        "models/gemini-3.8-flash"
    )

    # ==================================================
    # Properties
    # ==================================================

    @property
    def access_token(self):

        return (
            self.ARIIA_ACCESS_TOKEN
            or os.getenv(
                "ARIIA_ACCESS_TOKEN"
            )
            or os.getenv(
                "ariia_access_token"
            )
        )

    @property
    def scope_id(self):

        return (
            self.ARIIA_SCOPE_ID
            or os.getenv(
                "ARIIA_SCOPE_ID"
            )
            or os.getenv(
                "ariia_active_scope_id"
            )
        )

    @property
    def enterprise_id(self):

        return (
            self.ARIIA_ENTERPRISE_ID
            or os.getenv(
                "ARIIA_ENTERPRISE_ID"
            )
            or ""
        )

    @property
    def domain_ids(self) -> list[str]:
        """Resolve the configured domain identifiers as a normalized list."""
        configured_domain_ids = (
            self.ARIIA_DOMAIN_IDS
            or os.getenv("ARIIA_DOMAIN_IDS")
            or os.getenv("ariia_domain_ids")
            or ""
        )
        domain_ids = [
            domain.strip()
            for domain in configured_domain_ids.split(",")
            if domain.strip()
        ]
        return domain_ids

    @property
    def platform_headers(
        self
    ) -> Dict[str, str]:

        headers = {}

        if self.enterprise_id:

            headers[
                "X-Enterprise-Id"
            ] = self.enterprise_id

        if self.domain_ids:

            headers[
                "X-Domain-Id"
            ] = ",".join(self.domain_ids)

        return headers

    def get_service_url(
        self,
        override: Optional[str] = None
    ) -> str:

        return (
            override
            or self.PLATFORM_BACKEND_URL
            or self.BASE_URL
        ).rstrip("/")


settings = Settings()