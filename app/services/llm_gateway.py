import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.config.settings import settings
from app.services.copilot_service import CopilotService
from app.services.gemini_service import GeminiService
from app.services.groq_service import GroqService

logger = logging.getLogger(__name__)

ProviderFactory = Callable[[], Any]


class LLMGateway:
    """Provider-neutral LLM facade with configurable primary routing and failover."""

    _registered_providers: Dict[str, ProviderFactory] = {}
    _fallback_order = ("groq",)

    def __init__(
        self,
        provider: Optional[str] = None,
        provider_factories: Optional[Dict[str, ProviderFactory]] = None,
    ) -> None:
        self.provider = (provider or settings.LLM_PROVIDER).strip().lower()
        self._provider_factories = {
            "groq": GroqService,
            "copilot": CopilotService,
            "gemini": GeminiService,
            **self._registered_providers,
            **(provider_factories or {}),
        }
        if self.provider not in self._provider_factories:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
        self._provider_instances: Dict[str, Any] = {}

    @classmethod
    def register_provider(cls, name: str, factory: ProviderFactory) -> None:
        """Register an additional provider adapter for future gateway expansion."""
        normalized_name = name.strip().lower()
        if not normalized_name:
            raise ValueError("Provider name cannot be empty.")
        cls._registered_providers[normalized_name] = factory

    @property
    def is_configured(self) -> bool:
        return any(
            service.is_configured
            for _, service in self._services()
        )

    def _services(self) -> List[Tuple[str, Any]]:
        ordered_providers = [self.provider]
        ordered_providers.extend(
            name
            for name in self._fallback_order
            if name != self.provider and name in self._provider_factories
        )
        ordered_providers.extend(
            name
            for name in self._provider_factories
            if name not in ordered_providers
        )

        services: List[Tuple[str, Any]] = []
        for name in ordered_providers:
            service = self._provider_instances.get(name)
            if service is None:
                service = self._provider_factories[name]()
                self._provider_instances[name] = service
            if service.is_configured:
                services.append((name, service))
        return services

    async def _invoke(self, method: str, *args: Any, **kwargs: Any) -> Any:
        services = self._services()
        if not services:
            raise RuntimeError(
                f"No configured LLM provider is available for {self.provider!r}."
            )

        last_error: Optional[Exception] = None
        for index, (provider, service) in enumerate(services):
            try:
                return await getattr(service, method)(*args, **kwargs)
            except Exception as exc:
                last_error = exc
                if index + 1 < len(services):
                    logger.warning(
                        "LLM provider failed; trying configured fallback",
                        extra={
                            "provider": provider,
                            "fallback_provider": services[index + 1][0],
                        },
                        exc_info=True,
                    )
                else:
                    logger.error(
                        "All configured LLM providers failed",
                        extra={"provider": provider},
                        exc_info=True,
                    )

        if last_error is None:
            raise RuntimeError(
                "LLM provider invocation ended without a result or error."
            )
        raise last_error

    async def generate_text(self, *args: Any, **kwargs: Any) -> str:
        return await self._invoke("generate_text", *args, **kwargs)

    async def generate_json(self, *args: Any, **kwargs: Any) -> Any:
        return await self._invoke("generate_json", *args, **kwargs)

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        return await self._invoke("ainvoke", *args, **kwargs)

    @staticmethod
    def get_service() -> "LLMGateway":
        """Keep the established factory call while exposing the gateway itself."""
        return LLMGateway(settings.LLM_PROVIDER)


# Preserve imports used by existing integrations.
GatewayService = LLMGateway
