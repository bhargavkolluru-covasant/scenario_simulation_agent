import json
import logging
import re
from typing import Any, Dict, List, Optional, Type, Union

import httpx
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_groq import ChatGroq
from pydantic import BaseModel
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.config.settings import settings

logger = logging.getLogger(__name__)


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError, TimeoutError)):
        return True

    status_code = getattr(exc, "status_code", None)
    if status_code is None:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int):
        return status_code in {408, 409, 429} or status_code >= 500

    return type(exc).__name__ in {
        "APIConnectionError",
        "APITimeoutError",
        "InternalServerError",
        "RateLimitError",
    }


class GroqService:
    """Async LangChain adapter for Groq text and structured JSON generation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_output_tokens: int = 4096,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.timeout = timeout if timeout is not None else settings.GROQ_TIMEOUT
        self.max_retries = (
            max_retries if max_retries is not None else settings.GROQ_MAX_RETRIES
        )
        self._llm: Optional[ChatGroq] = None

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def get_llm(self) -> ChatGroq:
        if not self.is_configured:
            raise ValueError("GROQ_API_KEY is not configured.")
        if self._llm is None:
            logger.info(
                "Initializing Groq model",
                extra={"provider": "groq", "model": self.model},
            )
            self._llm = ChatGroq(
                model=self.model,
                api_key=self.api_key,
                temperature=self.temperature,
                max_tokens=self.max_output_tokens,
                timeout=self.timeout,
                max_retries=0,
            )
        return self._llm

    async def ainvoke(
        self,
        input_data: Union[str, List[Union[BaseMessage, str]]],
        **kwargs: Any,
    ) -> AIMessage:
        logger.info(
            "Calling Groq",
            extra={"provider": "groq", "model": self.model},
        )
        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception(_should_retry),
                stop=stop_after_attempt(max(1, self.max_retries + 1)),
                wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
                reraise=True,
            ):
                with attempt:
                    response = await self.get_llm().ainvoke(input_data, **kwargs)
            logger.info(
                "Received Groq response",
                extra={"provider": "groq", "model": self.model},
            )
            return response
        except Exception:
            logger.exception(
                "Groq request failed",
                extra={"provider": "groq", "model": self.model},
            )
            raise

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        messages: List[BaseMessage] = []
        if system_instruction:
            messages.append(SystemMessage(content=system_instruction))
        messages.append(HumanMessage(content=prompt))
        response = await self.ainvoke(messages, **kwargs)
        return str(response.content).strip()

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
        **kwargs: Any,
    ) -> Any:
        text = await self.generate_text(prompt, system_instruction, **kwargs)
        json_text = self._extract_json_substring(text)
        try:
            result: Any = json.loads(json_text)
        except json.JSONDecodeError as exc:
            logger.error(
                "Groq returned invalid JSON",
                extra={"provider": "groq", "model": self.model},
                exc_info=True,
            )
            raise ValueError("Groq did not return valid JSON.") from exc

        if schema is not None:
            if not isinstance(schema, type) or not issubclass(schema, BaseModel):
                raise TypeError("schema must be a Pydantic BaseModel type.")
            return schema.model_validate(result).model_dump()
        return result

    @staticmethod
    def _extract_json_substring(raw_text: str) -> str:
        text = raw_text.strip()
        if "```" in text:
            matches = re.findall(
                r"```(?:json)?\s*([\s\S]*?)\s*```",
                text,
                re.IGNORECASE,
            )
            if matches:
                return matches[0].strip()

        for opening, closing in (("{", "}"), ("[", "]")):
            start = text.find(opening)
            end = text.rfind(closing)
            if start >= 0 and end > start:
                return text[start : end + 1]
        return text
