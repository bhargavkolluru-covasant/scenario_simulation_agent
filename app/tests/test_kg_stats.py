import json

import pytest

from app.tests.kg_validation_support import live_kg_client


@pytest.mark.asyncio
async def test_knowledge_graph_stats() -> None:
    payload = await live_kg_client().get_stats()
    print(json.dumps(payload, indent=2, default=str))
    assert payload is not None
