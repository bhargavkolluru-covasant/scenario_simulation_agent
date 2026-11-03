import os
from typing import Optional

import pytest

from app.clients.knowledge_graph_client import KnowledgeGraphClient
from app.config.settings import settings


def live_kg_client() -> KnowledgeGraphClient:
    if os.getenv("RUN_KG_VALIDATION") != "1":
        pytest.skip("Set RUN_KG_VALIDATION=1 to call the live Knowledge Graph API.")
    if not settings.access_token:
        pytest.skip("Set ARIIA_ACCESS_TOKEN to authenticate live Knowledge Graph tests.")
    return KnowledgeGraphClient()


def configured_node_id() -> Optional[str]:
    value = os.getenv("KG_NODE_ID", "").strip()
    return value or None


def configured_node_type() -> Optional[str]:
    value = os.getenv("KG_NODE_TYPE", "").strip()
    return value or None
