import json
import logging
import re
from typing import Any, Dict, List, Optional, Type, Union

import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from app.config.settings import settings

logger = logging.getLogger(__name__)


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


class CopilotService:
    """Async client for the OpenAI-compatible GitHub Copilot API Gateway."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self.base_url = (base_url or settings.COPILOT_BASE_URL).rstrip("/")
        self.model = model or settings.COPILOT_MODEL
        self.timeout = timeout if timeout is not None else settings.COPILOT_TIMEOUT
        self.max_retries = (
            max_retries if max_retries is not None else settings.COPILOT_MAX_RETRIES
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.model)

    async def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async for attempt in AsyncRetrying(
            retry=retry_if_exception(_should_retry),
            stop=stop_after_attempt(max(1, self.max_retries + 1)),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
            reraise=True,
        ):
            with attempt:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                    )
                    response.raise_for_status()
                    result = response.json()
                    if not isinstance(result, dict):
                        raise ValueError(
                            "Copilot gateway returned a non-object response."
                        )
                    return result
        raise RuntimeError("Copilot gateway retry loop exited unexpectedly.")

    async def _generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        messages: List[Dict[str, str]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
        }
        if response_format:
            payload["response_format"] = response_format

        logger.info(
            "Calling Copilot API gateway",
            extra={"provider": "copilot", "model": self.model},
        )
        try:
            result = await self._post(payload)
            content = result["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise ValueError("Copilot gateway response content is not text.")
            logger.info(
                "Received Copilot API gateway response",
                extra={"provider": "copilot", "model": self.model},
            )
            return content.strip()
        except Exception:
            logger.exception(
                "Copilot API gateway request failed",
                extra={"provider": "copilot", "model": self.model},
            )
            raise

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        return await self._generate(prompt, system_instruction)

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        text = await self._generate(
            prompt,
            system_instruction,
            response_format={"type": "json_object"},
        )
        try:
            parsed: Any = json.loads(self._extract_json(text))
        except json.JSONDecodeError as exc:
            logger.error("Copilot returned invalid JSON", exc_info=True)
            raise ValueError("Copilot did not return valid JSON.") from exc

        if schema is not None:
            if not issubclass(schema, BaseModel):
                raise TypeError("schema must be a Pydantic BaseModel type.")
            return schema.model_validate(parsed).model_dump()
        if not isinstance(parsed, dict):
            raise ValueError("Copilot JSON response must be an object.")
        return parsed

    async def ainvoke(
        self,
        input_data: Union[str, List[Union[BaseMessage, str]]],
        **kwargs: Any,
    ) -> AIMessage:
        system_parts: List[str] = []
        user_parts: List[str] = []
        if isinstance(input_data, str):
            user_parts.append(input_data)
        else:
            for message in input_data:
                if isinstance(message, SystemMessage):
                    system_parts.append(str(message.content))
                elif isinstance(message, HumanMessage):
                    user_parts.append(str(message.content))
                elif isinstance(message, BaseMessage):
                    user_parts.append(str(message.content))
                else:
                    user_parts.append(str(message))
        response = await self.generate_text(
            prompt="\n".join(user_parts),
            system_instruction="\n".join(system_parts) or None,
        )
        return AIMessage(content=response)

    @staticmethod
    def _extract_json(text: str) -> str:
        cleaned = text.strip()
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if fenced:
            return fenced.group(1).strip()

        start_object = cleaned.find("{")
        end_object = cleaned.rfind("}")
        if start_object >= 0 and end_object > start_object:
            return cleaned[start_object : end_object + 1]

        start_array = cleaned.find("[")
        end_array = cleaned.rfind("]")
        if start_array >= 0 and end_array > start_array:
            return cleaned[start_array : end_array + 1]
        return cleaned
