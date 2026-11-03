import logging
from typing import Any, Dict
from app.clients.knowledge_graph_client import KnowledgeGraphClient
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


def _merge_graph_items(existing: list, incoming: list) -> list:
    merged = []
    seen = set()
    for item in existing + incoming:
        if isinstance(item, dict):
            identity = next(
                (
                    str(item[key])
                    for key in ("id", "node_id", "uuid", "key")
                    if item.get(key) is not None
                ),
                repr(item),
            )
        else:
            identity = repr(item)
        if identity not in seen:
            seen.add(identity)
            merged.append(item)
    return merged


async def knowledge_graph_node(state: SimulationState) -> SimulationState:
    """
    LangGraph Node: Knowledge Graph Traversal & Relationship Discovery
    Traverses graph relationships, extracts graph statistics, and enriches entity context.
    """
    logger.info("[knowledge_graph_node] Querying Knowledge Graph")
    state["current_node"] = "knowledge_graph"
    client = KnowledgeGraphClient(
        auth_token=state.get("access_token"),
        enterprise_id=state.get("enterprise_id"),
        domain_ids=state.get("domain_ids"),
        scope_id=state.get("scope_id"),
    )

    service = KnowledgeGraphService(client)
    graph_data: Dict[str, Any] = {"nodes": [], "edges": [], "stats": {}}
    try:
        response = await client.get_knowledge_graph(limit=100, include_stats=True)
        if isinstance(response, dict):
            normalized = service.normalize_graph(response)
            graph_data = {
                **normalized,
                "stats": response.get("stats", {}),
            }
        summary = service.summarize_graph(graph_data, graph_data.get("stats"))
        scenario = state.get("scenario", {})
        if not isinstance(scenario, dict):
            scenario = {}
        entity_match_summary = state.get("entity_match_summary", {})
        if not isinstance(entity_match_summary, dict):
            entity_match_summary = {}
        target_entity = (
            scenario.get("target_entity")
            or entity_match_summary.get("target_entity")
            or ""
        )
        resolved = service.resolve_entity(graph_data, target_entity)

        related_entities = []
        dependency_paths = []
        blast_radius: Dict[str, Any] = {
            "root_entity": target_entity,
            "max_depth": 5,
            "affected_entity_count": 0,
            "affected_entities": [],
            "affected_entities_by_type": {},
            "blast_radius_score": 0.0,
        }
        root_cause_candidates = []
        if resolved:
            resolved_id = resolved.get("resolved_node_id") or ""
            try:
                subgraph_response = await client.get_subgraph(resolved_id)
                subgraph = service.normalize_graph(subgraph_response)
                graph_data["nodes"] = _merge_graph_items(
                    graph_data["nodes"],
                    subgraph["nodes"],
                )
                graph_data["edges"] = _merge_graph_items(
                    graph_data["edges"],
                    subgraph["edges"],
                )
                summary = service.summarize_graph(
                    graph_data,
                    graph_data.get("stats"),
                )
            except Exception as exc:
                logger.warning(
                    "[knowledge_graph_node] Target subgraph unavailable for %s: %s",
                    resolved_id,
                    exc,
                )
            related_entities = service.find_related_entities(
                graph_data,
                resolved_id,
                max_depth=5,
            )
            dependency_paths = service.compute_dependency_chain(
                graph_data,
                resolved_id,
                max_depth=5,
            )
            blast_radius = service.compute_blast_radius(
                graph_data,
                resolved_id,
                max_depth=5,
            )
            root_cause_candidates = service.find_root_cause_candidates(
                graph_data,
                target_entity,
                rules=state.get("rules", []),
                matched_dashboard_records=state.get("matched_dashboard_records", []),
                kpi_insights=state.get("kpi_insights", {}),
                related_entities=related_entities,
            )
        elif target_entity:
            summary["explanation"] += (
                f" Scenario target '{target_entity}' did not match a graph node."
            )

        if not summary.get("usable_for_simulation"):
            summary["explanation"] = (
                "Graph unavailable or no relationships found. "
                + str(summary.get("explanation") or "")
            ).strip()
        graph_data.update({
            "total_nodes": len(graph_data["nodes"]),
            "total_edges": len(graph_data["edges"]),
            "graph_summary": summary,
            "resolved_entity": resolved,
            "related_entities": related_entities,
            "dependency_paths": dependency_paths,
            "blast_radius": blast_radius,
            "root_cause_candidates": root_cause_candidates,
        })
        state["graph_summary"] = summary
        state["related_entities"] = related_entities
        state["dependency_paths"] = dependency_paths
        state["blast_radius"] = blast_radius
        state["root_cause_candidates"] = root_cause_candidates
        logger.info(
            "[knowledge_graph_node] Loaded %d nodes, %d edges, %d related entities",
            len(graph_data["nodes"]),
            len(graph_data["edges"]),
            len(related_entities),
        )

    except Exception as exc:
        logger.warning(
            "[knowledge_graph_node] Knowledge graph enrichment unavailable: %s",
            exc,
            exc_info=True,
        )
        summary = service.summarize_graph(graph_data, graph_data.get("stats"))
        summary["usable_for_simulation"] = False
        summary["explanation"] = (
            "Graph unavailable or no relationships found. Simulation continues "
            "without graph-derived propagation."
        )
        graph_data.update({
            "total_nodes": len(graph_data["nodes"]),
            "total_edges": len(graph_data["edges"]),
            "graph_summary": summary,
            "resolved_entity": None,
            "related_entities": [],
            "dependency_paths": [],
            "blast_radius": {
                "root_entity": "",
                "max_depth": 5,
                "affected_entity_count": 0,
                "affected_entities": [],
                "affected_entities_by_type": {},
                "blast_radius_score": 0.0,
            },
            "root_cause_candidates": [],
        })
        state["graph_summary"] = summary
        state["related_entities"] = []
        state["dependency_paths"] = []
        state["blast_radius"] = graph_data["blast_radius"]
        state["root_cause_candidates"] = []

    state["knowledge_graph_data"] = graph_data

    return state
