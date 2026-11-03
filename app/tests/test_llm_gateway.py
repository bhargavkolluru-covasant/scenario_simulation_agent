import pytest

from app.config.settings import settings
from app.services.llm_gateway import LLMGateway


@pytest.mark.asyncio
async def test_llm_gateway_live_returns_json():
    if not settings.GROQ_API_KEY:
        pytest.skip("GROQ_API_KEY is not configured.")

    gateway = LLMGateway(provider="groq")
    result = await gateway.generate_json(
        'Return JSON {"status":"ok"}',
        system_instruction="Return only a JSON object with status set to ok.",
    )
    print(result)

    assert result.get("status") == "ok"


@pytest.mark.asyncio
async def test_llm_gateway_returns_json(capsys):
    class FakeProvider:
        is_configured = True

        async def generate_json(self, prompt, **kwargs):
            assert prompt == 'Return JSON {"status":"ok"}'
            return {"status": "ok"}

    gateway = LLMGateway(
        provider="groq",
        provider_factories={"groq": FakeProvider},
    )
    result = await gateway.generate_json('Return JSON {"status":"ok"}')
    print(result)

    assert result == {"status": "ok"}
    assert capsys.readouterr().out.strip() == "{'status': 'ok'}"


@pytest.mark.asyncio
async def test_llm_gateway_falls_back_in_provider_order():
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

    gateway = LLMGateway(
        provider="groq",
        provider_factories={
            "groq": provider("groq", fails=True),
            "copilot": provider("copilot", fails=True),
            "gemini": provider("gemini", response="hello"),
        },
    )

    assert await gateway.generate_text("Say hello") == "hello"
    assert called == ["groq", "copilot", "gemini"]
