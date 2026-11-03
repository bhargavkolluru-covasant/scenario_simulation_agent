import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from app.config.settings import settings
from app.services import groq_service
from app.services.groq_service import GroqService


@pytest.mark.asyncio
async def test_groq_live_says_hello():
    if not settings.GROQ_API_KEY:
        pytest.skip("GROQ_API_KEY is not configured.")

    result = await GroqService().generate_text("Say hello")
    print(result)

    assert result.strip()


@pytest.mark.asyncio
async def test_groq_service_says_hello(monkeypatch, capsys):
    captured = {}

    class FakeChatGroq:
        def __init__(self, **kwargs):
            captured["configuration"] = kwargs

        async def ainvoke(self, messages, **kwargs):
            captured["messages"] = messages
            return AIMessage(content="Hello!")

    monkeypatch.setattr(groq_service, "ChatGroq", FakeChatGroq)
    service = GroqService(api_key="test-key", timeout=12, max_retries=2)

    result = await service.generate_text(
        "Say hello",
        system_instruction="Reply briefly.",
    )
    print(result)

    assert result == "Hello!"
    assert captured["messages"] == [
        SystemMessage(content="Reply briefly."),
        HumanMessage(content="Say hello"),
    ]
    assert captured["configuration"]["timeout"] == 12
    assert captured["configuration"]["max_retries"] == 0
    assert capsys.readouterr().out.strip() == "Hello!"


@pytest.mark.asyncio
async def test_groq_service_extracts_and_validates_json(monkeypatch):
    class Result(BaseModel):
        status: str

    service = GroqService(api_key="test-key")

    async def fake_generate_text(prompt, system_instruction=None, **kwargs):
        return 'Result:\n```json\n{"status": "ok"}\n```'

    monkeypatch.setattr(service, "generate_text", fake_generate_text)

    result = await service.generate_json("Return JSON.", schema=Result)

    assert result == {"status": "ok"}
