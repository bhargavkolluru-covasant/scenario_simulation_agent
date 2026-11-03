import httpx
import pytest

from app.config.settings import settings
from app.services.copilot_service import CopilotService
from app.services import llm_gateway
from app.services.llm_gateway import LLMGateway


@pytest.mark.asyncio
async def test_local_copilot_gateway_says_hello():
    service = CopilotService(
        base_url=settings.COPILOT_BASE_URL,
        model=settings.COPILOT_MODEL,
        timeout=5,
        max_retries=1,
    )

    try:
        response = await service.generate_text("Say hello")
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        pytest.skip(f"Local Copilot gateway is not available: {exc}")

    assert isinstance(response, str)
    assert response.strip()


@pytest.mark.asyncio
async def test_copilot_generation_builds_openai_payload(monkeypatch):
    service = CopilotService(max_retries=1)
    requests = []

    async def fake_post(payload):
        requests.append(payload)
        if "response_format" in payload:
            content = '{"message": "hello"}'
        else:
            content = "Hello!"
        return {"choices": [{"message": {"content": content}}]}

    monkeypatch.setattr(service, "_post", fake_post)

    text = await service.generate_text(
        "Say hello",
        system_instruction="Be concise.",
    )
    data = await service.generate_json(
        'Return {"message": "hello"}.',
        system_instruction="Return JSON only.",
    )

    assert text == "Hello!"
    assert data == {"message": "hello"}
    assert requests[0]["model"] == settings.COPILOT_MODEL
    assert requests[0]["messages"] == [
        {"role": "system", "content": "Be concise."},
        {"role": "user", "content": "Say hello"},
    ]
    assert requests[1]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_gateway_falls_back_from_copilot_to_groq_then_gemini(monkeypatch):
    called = []

    def provider(name, response=None, fails=False):
        class FakeProvider:
            is_configured = True

            async def generate_text(self, prompt, **kwargs):
                called.append(name)
                if fails:
                    raise RuntimeError(f"{name} unavailable")
                return response

        return FakeProvider

    monkeypatch.setattr(settings, "LLM_PROVIDER", "copilot")
    monkeypatch.setattr(
        llm_gateway, "CopilotService", provider("copilot", fails=True)
    )
    monkeypatch.setattr(
        llm_gateway, "GroqService", provider("groq", fails=True)
    )
    monkeypatch.setattr(
        llm_gateway, "GeminiService", provider("gemini", response="hello")
    )

    response = await LLMGateway.get_service().generate_text("Say hello")

    assert response == "hello"
    assert called == ["copilot", "groq", "gemini"]
