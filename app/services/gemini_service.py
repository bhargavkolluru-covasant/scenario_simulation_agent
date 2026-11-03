import json
import logging
import re
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
)

from langchain_google_genai import (
    ChatGoogleGenerativeAI
)

from app.config.settings import settings

logger = logging.getLogger(__name__)


class GeminiService:
    """
    Enterprise Gemini Service.

    Responsibilities:
    - Centralized Gemini access
    - Async LLM invocation
    - Structured JSON generation
    - Timeout protection
    - Response validation
    - Clean fallback handling
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_output_tokens: int = 4096,
    ):
        self.api_key = (
            api_key or settings.GEMINI_API_KEY
        )

        self.model = (
            model
            or settings.GEMINI_MODEL
            or "models/gemini-3.8-flash"
        )

        self.temperature = temperature

        self.max_output_tokens = (
            max_output_tokens
        )

        self._llm: Optional[
            ChatGoogleGenerativeAI
        ] = None

    @property
    def is_configured(self) -> bool:
        return bool(
            self.api_key
            and self.api_key.strip()
        )

    def get_llm(
        self,
    ) -> ChatGoogleGenerativeAI:
        """
        Singleton initialization.
        """

        if self._llm is None:

            if not self.is_configured:
                raise ValueError(
                    "GEMINI_API_KEY is not configured."
                )

            logger.info(
                f"[GeminiService] Initializing model={self.model}"
            )

            self._llm = (
                ChatGoogleGenerativeAI(
                    model=self.model,
                    google_api_key=self.api_key,
                    temperature=self.temperature,
                    max_output_tokens=self.max_output_tokens,
                    timeout=30,
                )
            )

        return self._llm

    async def ainvoke(
        self,
        input_data: Union[
            str,
            List[
                Union[
                    BaseMessage,
                    str
                ]
            ],
        ],
        **kwargs,
    ):

        llm = self.get_llm()

        try:

            logger.info(
                f"[GeminiService] Calling {self.model}"
            )

            response = await llm.ainvoke(
                input_data,
                **kwargs,
            )

            logger.info(
                f"[GeminiService] Response received from {self.model}"
            )

            return response

        except Exception as exc:

            logger.error(
                "[GeminiService] Gemini request failed: "
                f"{exc}",
                exc_info=True,
            )

            raise

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[
            str
        ] = None,
        **kwargs,
    ) -> str:
        """
        Generate text response.
        """

        messages = []

        if system_instruction:

            messages.append(
                SystemMessage(
                    content=system_instruction
                )
            )

        messages.append(
            HumanMessage(
                content=prompt
            )
        )

        response = await self.ainvoke(
            messages,
            **kwargs,
        )

        if hasattr(response, "content"):
            return str(
                response.content
            ).strip()

        return str(response).strip()

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[
            str
        ] = None,
        schema: Optional[
            Type[BaseModel]
        ] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate strict JSON.
        """

        text_response = (
            await self.generate_text(
                prompt=prompt,
                system_instruction=system_instruction,
                **kwargs,
            )
        )

        json_text = (
            self._extract_json_substring(
                text_response
            )
        )

        try:

            parsed_data = json.loads(
                json_text
            )

        except json.JSONDecodeError as exc:

            logger.error(
                "[GeminiService] Invalid JSON returned:\n"
                f"{text_response}",
                exc_info=True,
            )

            raise ValueError(
                "Gemini did not return valid JSON."
            ) from exc

        if (
            schema
            and issubclass(
                schema,
                BaseModel
            )
        ):
            validated = (
                schema.model_validate(
                    parsed_data
                )
            )

            return validated.model_dump()

        return parsed_data

    @staticmethod
    def _extract_json_substring(
        raw_text: str,
    ) -> str:
        """
        Extract JSON from markdown.
        """

        text = raw_text.strip()

        if "```" in text:

            pattern = (
                r"```(?:json)?\s*"
                r"([\s\S]*?)"
                r"\s*```"
            )

            matches = re.findall(
                pattern,
                text,
                re.IGNORECASE,
            )

            if matches:
                return matches[0].strip()

        start = text.find("{")
        end = text.rfind("}")

        if (
            start != -1
            and end != -1
            and end > start
        ):
            return text[
                start : end + 1
            ]

        start = text.find("[")
        end = text.rfind("]")

        if (
            start != -1
            and end != -1
            and end > start
        ):
            return text[
                start : end + 1
            ]

        return text


_gemini_service_instance = None


def get_gemini_service():
    global _gemini_service_instance

    if (
        _gemini_service_instance
        is None
    ):
        _gemini_service_instance = (
            GeminiService()
        )

    return (
        _gemini_service_instance
    )


def get_llm(
    model: Optional[str] = None,
    temperature: float = 0.0,
):

    effective_model = (
        model
        or settings.GEMINI_MODEL
        or "gemini-3.8-flash"
    )

    return ChatGoogleGenerativeAI(
        model=effective_model,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperature,
        timeout=30,
    )