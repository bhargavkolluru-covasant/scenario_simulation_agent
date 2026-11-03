import logging
from typing import Any, Dict, List
from app.clients.semantic_registry_client import SemanticRegistryClient
from app.models.canonical import BusinessEntity
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


async def semantic_registry_node(state: SimulationState) -> SimulationState:
    """
    LangGraph Node: Semantic Registry Discovery
    Discovers business entities, extracts metadata attributes, and initializes canonical entities.
    """
    logger.info("[semantic_registry_node] Discovering entities from Semantic Registry")
    state["current_node"] = "semantic_registry"
    client = SemanticRegistryClient()

    try:
        # Fetch entities list from registry
        registry_data = await client.get_semantic_registry()
        raw_entities = registry_data.get("entities", [])

        # If full registry has no entities, try the entities list endpoint
        if not raw_entities:
            entity_names = await client.get_entities()
            if isinstance(entity_names, list):
                raw_entities = [{"entity_name": name, "entity_type": "BusinessEntity"} for name in entity_names]

        # Convert to canonical BusinessEntity models
        canonical_entities: List[Dict[str, Any]] = []
        for idx, item in enumerate(raw_entities):
            if isinstance(item, dict):
                entity_name = item.get("entity_name", item.get("name", f"Entity_{idx}"))
                entity_id = item.get("entity_id", item.get("id", f"ENT-{idx:03d}"))
                entity_type = item.get("entity_type", item.get("type", "DomainEntity"))
                attributes = item.get("attributes", {})
                relationships = item.get("relationships", [])
            else:
                entity_name = str(item)
                entity_id = f"ENT-{idx:03d}"
                entity_type = "DomainEntity"
                attributes = {}
                relationships = []

            entity = BusinessEntity(
                entity_id=entity_id,
                entity_name=entity_name,
                entity_type=entity_type,
                attributes=attributes if isinstance(attributes, dict) else {},
                relationships=relationships if isinstance(relationships, list) else [],
            )
            canonical_entities.append(entity.model_dump())

        state["semantic_entities"] = canonical_entities
        logger.info(f"[semantic_registry_node] Discovered {len(canonical_entities)} canonical entities")

    except Exception as exc:
        logger.warning(f"[semantic_registry_node] Semantic registry retrieval warning: {exc}")
        # Provide safe fallback canonical entity based on query keywords
        query = state.get("query", "Default")
        fallback_entity = BusinessEntity(
            entity_id="ENT-ROOT",
            entity_name=query[:30],
            entity_type="QueryContext",
            attributes={"query": query},
            relationships=[],
        )
        state["semantic_entities"] = [fallback_entity.model_dump()]

    return state
