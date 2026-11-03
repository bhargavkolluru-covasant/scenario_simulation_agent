import logging
import re
from collections import Counter, deque
from typing import Any, Dict, List, Mapping, Optional, Tuple

from app.clients.knowledge_graph_client import KnowledgeGraphClient

logger = logging.getLogger(__name__)

_NODE_COLLECTION_KEYS = ("nodes", "vertices", "entities")
_EDGE_COLLECTION_KEYS = ("edges", "relationships", "links")
_WRAPPER_KEYS = ("data", "graph", "knowledge_graph", "result", "payload")
_NODE_COUNT_KEYS = ("total_nodes", "node_count", "nodes_count")
_EDGE_COUNT_KEYS = (
    "total_relationships",
    "total_edges",
    "relationship_count",
    "edges_count",
)


def _find_graph_payload(payload: Any) -> Mapping[str, Any]:
    """Find a graph object nested in common API response envelopes."""
    if not isinstance(payload, Mapping):
        return {}
    if any(key in payload for key in (*_NODE_COLLECTION_KEYS, *_EDGE_COLLECTION_KEYS)):
        return payload

    for key in _WRAPPER_KEYS:
        nested = payload.get(key)
        if isinstance(nested, Mapping):
            graph = _find_graph_payload(nested)
            if graph:
                return graph
    for value in payload.values():
        if isinstance(value, Mapping):
            graph = _find_graph_payload(value)
            if graph:
                return graph
    return {}


def _collection(payload: Mapping[str, Any], keys: Tuple[str, ...]) -> List[Any]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, Mapping):
            return [
                {"id": item_id, **item} if isinstance(item, Mapping) else {"id": item_id}
                for item_id, item in value.items()
            ]
    return []


def _first_value(item: Mapping[str, Any], keys: Tuple[str, ...]) -> Any:
    for key in keys:
        value = item.get(key)
        if value is not None and value != "":
            return value
    return None


def _find_stats_payload(payload: Any) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    if any(key in payload for key in (*_NODE_COUNT_KEYS, *_EDGE_COUNT_KEYS)):
        return payload
    for key in ("stats", *_WRAPPER_KEYS):
        nested = payload.get(key)
        if isinstance(nested, Mapping):
            stats = _find_stats_payload(nested)
            if stats:
                return stats
    for value in payload.values():
        if isinstance(value, Mapping):
            stats = _find_stats_payload(value)
            if stats:
                return stats
    return {}


def _nonnegative_count(payload: Mapping[str, Any], keys: Tuple[str, ...]) -> Optional[int]:
    value = _first_value(payload, keys)
    if isinstance(value, bool):
        return None
    try:
        count = int(value)
    except (TypeError, ValueError):
        return None
    return count if count >= 0 else None


def _count_distribution(payload: Mapping[str, Any], key: str) -> Dict[str, int]:
    distribution = payload.get(key)
    if not isinstance(distribution, Mapping):
        return {}
    counts = {}
    for item_type, value in distribution.items():
        if isinstance(value, bool):
            continue
        try:
            count = int(value)
        except (TypeError, ValueError):
            continue
        if count >= 0:
            counts[str(item_type)] = count
    return counts


def _node_identifier(node: Any) -> Optional[str]:
    if not isinstance(node, Mapping):
        return None
    value = _first_value(node, ("id", "node_id", "uuid", "key"))
    return str(value) if value is not None else None


def _node_name(node: Any) -> Optional[str]:
    if not isinstance(node, Mapping):
        return None
    value = _first_value(
        node,
        ("name", "entity_name", "display_name", "title", "label", "value"),
    )
    if value is None:
        properties = node.get("properties")
        if isinstance(properties, Mapping):
            value = _first_value(
                properties,
                ("name", "entity_name", "display_name", "title", "label"),
            )
    if value is None:
        identifier = _node_identifier(node)
        return identifier
    return str(value)


def _node_type(node: Any) -> Optional[str]:
    if not isinstance(node, Mapping):
        return None
    value = _first_value(node, ("node_type", "entity_type", "type"))
    if value is None:
        properties = node.get("properties")
        if isinstance(properties, Mapping):
            value = _first_value(properties, ("node_type", "entity_type", "type"))
    if value is None:
        labels = node.get("labels")
        if isinstance(labels, list) and labels:
            value = labels[0]
    return str(value) if value is not None else None


def _relationship_type(edge: Any) -> Optional[str]:
    if not isinstance(edge, Mapping):
        return None
    value = _first_value(
        edge,
        ("relationship_type", "relation_type", "type", "predicate", "label", "name"),
    )
    return str(value) if value is not None else None


def _edge_endpoints(edge: Any) -> Tuple[Optional[str], Optional[str]]:
    if not isinstance(edge, Mapping):
        return None, None
    source = _first_value(edge, ("source", "source_id", "from", "start"))
    target = _first_value(edge, ("target", "target_id", "to", "end"))
    if isinstance(source, Mapping):
        source = _first_value(source, ("id", "node_id", "uuid"))
    if isinstance(target, Mapping):
        target = _first_value(target, ("id", "node_id", "uuid"))
    return (
        str(source) if source is not None else None,
        str(target) if target is not None else None,
    )


def _normalized_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _node_aliases(node: Any) -> List[str]:
    if not isinstance(node, Mapping):
        return []
    aliases = []
    for value in (
        _node_identifier(node),
        _node_name(node),
        node.get("entity_name"),
        node.get("name"),
    ):
        normalized = _normalized_text(value)
        if normalized and normalized not in aliases:
            aliases.append(normalized)
    properties = node.get("properties")
    if isinstance(properties, Mapping):
        for key in ("name", "entity_name", "display_name", "title", "code", "reference"):
            normalized = _normalized_text(properties.get(key))
            if normalized and normalized not in aliases:
                aliases.append(normalized)
    return aliases


def _record_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(
            f"{key} {_record_text(item)}" for key, item in value.items()
        ).casefold()
    if isinstance(value, (list, tuple)):
        return " ".join(_record_text(item) for item in value).casefold()
    return str(value or "").casefold()


def _records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("kpis", "insights", "items", "results", "data", "recent_kpis"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    for value in payload.values():
        records = _records(value)
        if records:
            return records
    return []


class KnowledgeGraphService:
    """Normalize Knowledge Graph API responses and summarize simulation evidence."""

    def __init__(self, client: Optional[KnowledgeGraphClient] = None) -> None:
        self.client = client or KnowledgeGraphClient()

    @staticmethod
    def normalize_graph(graph_response: Any) -> Dict[str, Any]:
        graph = _find_graph_payload(graph_response)
        return {
            "nodes": _collection(graph, _NODE_COLLECTION_KEYS),
            "edges": _collection(graph, _EDGE_COLLECTION_KEYS),
        }

    @staticmethod
    def summarize_graph(
        graph_response: Any,
        stats_response: Any = None,
    ) -> Dict[str, Any]:
        """Return graph counts, type distributions, and a structural usability check."""
        if graph_response is None:
            graph_response = {}
        if stats_response is None:
            stats_response = graph_response

        graph = KnowledgeGraphService.normalize_graph(graph_response)
        stats = _find_stats_payload(stats_response)
        nodes = graph["nodes"]
        edges = graph["edges"]
        node_type_counts = Counter(
            node_type
            for node in nodes
            if (node_type := _node_type(node)) is not None
        )
        relationship_type_counts = Counter(
            relationship_type
            for edge in edges
            if (relationship_type := _relationship_type(edge)) is not None
        )
        total_nodes = _nonnegative_count(stats, _NODE_COUNT_KEYS)
        total_edges = _nonnegative_count(stats, _EDGE_COUNT_KEYS)
        node_types = _count_distribution(stats, "node_types")
        relationship_types = _count_distribution(stats, "relationship_types")
        if not node_types:
            node_types = dict(node_type_counts)
        if not relationship_types:
            relationship_types = dict(relationship_type_counts)
        total_nodes = len(nodes) if total_nodes is None else total_nodes
        total_edges = len(edges) if total_edges is None else total_edges
        known_node_ids = {
            node_id for node in nodes if (node_id := _node_identifier(node)) is not None
        }
        node_types_by_id = {
            node_id: node_type
            for node in nodes
            if (node_id := _node_identifier(node)) is not None
            and (node_type := _node_type(node)) is not None
        }
        connected_node_types = set()
        has_connected_edge = False
        for edge in edges:
            source, target = _edge_endpoints(edge)
            if (
                source is None
                or target is None
                or source not in known_node_ids
                or target not in known_node_ids
            ):
                continue
            has_connected_edge = True
            if source in node_types_by_id:
                connected_node_types.add(node_types_by_id[source])
            if target in node_types_by_id:
                connected_node_types.add(node_types_by_id[target])
        usable_for_simulation = bool(nodes and edges and has_connected_edge)

        if total_nodes == 0:
            explanation = "The graph API returned no nodes."
        elif total_edges == 0:
            explanation = "The graph has nodes but no relationships to propagate impact."
        elif not has_connected_edge:
            explanation = (
                "The graph has nodes and relationships, but the returned edges could "
                "not be matched to known node IDs."
            )
        else:
            explanation = (
                "The graph contains nodes and relationships whose endpoints resolve to "
                "known nodes, so it can support relationship-based impact propagation. "
                "Business relevance and data freshness still need domain validation."
            )

        summary = {
            "graph_exists": bool(total_nodes or total_edges),
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "node_types": dict(sorted(node_types.items())),
            "relationship_types": dict(sorted(relationship_types.items())),
            "impact_propagation_candidate_types": sorted(connected_node_types),
            "usable_for_simulation": usable_for_simulation,
            "explanation": explanation,
        }
        logger.info(
            "Knowledge Graph summary: nodes=%d edges=%d usable=%s",
            summary["total_nodes"],
            summary["total_edges"],
            usable_for_simulation,
        )
        return summary

    async def graph_summary(
        self,
        graph_response: Any = None,
        stats_response: Any = None,
    ) -> Dict[str, Any]:
        """Backward-compatible async summary helper that fetches graph when omitted."""
        if graph_response is None:
            graph_response = await self.client.get_graph()
        return self.summarize_graph(graph_response, stats_response)

    def resolve_entity(
        self,
        graph_response: Any,
        target_entity: str,
    ) -> Optional[Dict[str, Any]]:
        """Resolve a scenario target to the best exact or unambiguous partial graph node."""
        target = _normalized_text(target_entity)
        if not target:
            return None
        nodes = self.normalize_graph(graph_response)["nodes"]
        exact_matches = []
        partial_matches = []
        for node in nodes:
            if not isinstance(node, Mapping):
                continue
            aliases = _node_aliases(node)
            if target in aliases:
                exact_matches.append(node)
            elif any(target in alias or alias in target for alias in aliases if alias):
                partial_matches.append(node)
        if len(exact_matches) == 1:
            matches = exact_matches
            match_type = "exact"
            score = 1.0
        elif len(exact_matches) > 1:
            return None
        elif len(partial_matches) == 1:
            matches = partial_matches
            match_type = "partial"
            score = 0.75
        else:
            return None
        matches.sort(key=lambda node: (_node_name(node) or "").casefold())
        node = matches[0]
        result = dict(node)
        result["resolved_node_id"] = _node_identifier(node)
        result["resolved_name"] = _node_name(node)
        result["resolved_type"] = _node_type(node)
        result["match_type"] = match_type
        result["match_score"] = score
        return result

    @staticmethod
    def _index_graph(graph_response: Any) -> Tuple[Dict[str, Any], Dict[str, List[Tuple[str, Any]]]]:
        graph = KnowledgeGraphService.normalize_graph(graph_response)
        nodes_by_id = {
            node_id: node
            for node in graph["nodes"]
            if (node_id := _node_identifier(node)) is not None
        }
        alias_to_id = {}
        for node_id, node in nodes_by_id.items():
            alias_to_id[node_id] = node_id
            for alias in _node_aliases(node):
                alias_to_id.setdefault(alias, node_id)

        adjacency: Dict[str, List[Tuple[str, Any]]] = {
            node_id: [] for node_id in nodes_by_id
        }
        for edge in graph["edges"]:
            source, target = _edge_endpoints(edge)
            source_id = alias_to_id.get(source) or alias_to_id.get(_normalized_text(source))
            target_id = alias_to_id.get(target) or alias_to_id.get(_normalized_text(target))
            if source_id is None or target_id is None:
                continue
            adjacency[source_id].append((target_id, edge))
            if source_id != target_id:
                adjacency[target_id].append((source_id, edge))
        return nodes_by_id, adjacency

    def find_related_entities(
        self,
        graph_response: Any,
        entity_id: str,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """Return deduplicated neighboring entities reachable within a bounded depth."""
        nodes_by_id, adjacency = self._index_graph(graph_response)
        root = entity_id if entity_id in nodes_by_id else None
        if root is None:
            normalized_id = _normalized_text(entity_id)
            root = next(
                (
                    node_id
                    for node_id, node in nodes_by_id.items()
                    if normalized_id in _node_aliases(node)
                ),
                None,
            )
        if root is None or max_depth < 1:
            return []

        results = []
        visited = {root}
        queue = deque([(root, 0, [_node_name(nodes_by_id[root]) or root], [])])
        while queue:
            current, depth, path_names, path_relationships = queue.popleft()
            if depth >= max_depth:
                continue
            for neighbor_id, edge in adjacency.get(current, []):
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                neighbor = nodes_by_id[neighbor_id]
                relationship = _relationship_type(edge) or "RELATED_TO"
                next_path = path_names + [_node_name(neighbor) or neighbor_id]
                next_relationships = path_relationships + [relationship]
                results.append({
                    "node_id": neighbor_id,
                    "name": _node_name(neighbor) or neighbor_id,
                    "node_type": _node_type(neighbor),
                    "depth": depth + 1,
                    "relationship_type": relationship,
                    "path": next_path,
                    "relationships": next_relationships,
                    "node": dict(neighbor) if isinstance(neighbor, Mapping) else neighbor,
                })
                queue.append((neighbor_id, depth + 1, next_path, next_relationships))
        return results

    def compute_blast_radius(
        self,
        graph_response: Any,
        entity_id: str,
        max_depth: int = 5,
    ) -> Dict[str, Any]:
        """Summarize reachable graph entities without assuming financial impact amounts."""
        nodes_by_id, _ = self._index_graph(graph_response)
        related = self.find_related_entities(graph_response, entity_id, max_depth)
        type_counts = Counter(
            item["node_type"] for item in related if item.get("node_type")
        )
        root = nodes_by_id.get(entity_id)
        total_graph_nodes = len(nodes_by_id)
        return {
            "root_entity": _node_name(root) if root else entity_id,
            "max_depth": max_depth,
            "affected_entity_count": len(related),
            "affected_entities": related,
            "affected_entities_by_type": dict(sorted(type_counts.items())),
            "blast_radius_score": round(
                len(related) / max(total_graph_nodes - 1, 1) * 100.0,
                1,
            ) if related else 0.0,
        }

    def compute_dependency_chain(
        self,
        graph_response: Any,
        entity_id: str,
        max_depth: int = 5,
        max_paths: int = 25,
    ) -> List[Dict[str, Any]]:
        """Return bounded simple paths beginning at the resolved scenario entity."""
        nodes_by_id, adjacency = self._index_graph(graph_response)
        if entity_id not in nodes_by_id:
            resolved = self.resolve_entity(graph_response, entity_id)
            entity_id = (resolved or {}).get("resolved_node_id") or ""
        if entity_id not in nodes_by_id or max_depth < 1:
            return []

        paths = []
        queue = deque([(entity_id, [entity_id], [])])
        while queue and len(paths) < max_paths:
            current, node_path, edge_path = queue.popleft()
            if edge_path:
                paths.append({
                    "entity_ids": node_path,
                    "entities": [
                        _node_name(nodes_by_id[node_id]) or node_id
                        for node_id in node_path
                    ],
                    "relationships": [
                        _relationship_type(edge) or "RELATED_TO"
                        for edge in edge_path
                    ],
                    "depth": len(edge_path),
                })
            if len(edge_path) >= max_depth:
                continue
            for neighbor_id, edge in adjacency.get(current, []):
                if neighbor_id in node_path:
                    continue
                if len(queue) >= max_paths:
                    break
                queue.append((neighbor_id, node_path + [neighbor_id], edge_path + [edge]))
        return paths

    def find_root_cause_candidates(
        self,
        graph_response: Any,
        target_entity: str,
        rules: Any = None,
        matched_dashboard_records: Any = None,
        kpi_insights: Any = None,
        related_entities: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Link risk signals to graph entities as hypotheses, never confirmed causes."""
        graph = self.normalize_graph(graph_response)
        resolved = self.resolve_entity(graph_response, target_entity)
        if not resolved:
            return []
        if related_entities is None:
            related_entities = self.find_related_entities(
                graph_response,
                resolved.get("resolved_node_id") or "",
            )
        name_to_entity = {
            _normalized_text(item.get("name")): item
            for item in related_entities
            if item.get("name")
        }
        name_to_entity[_normalized_text(resolved.get("resolved_name"))] = {
            "name": resolved.get("resolved_name"),
            "node_id": resolved.get("resolved_node_id"),
            "node_type": resolved.get("resolved_type"),
            "depth": 0,
            "path": [resolved.get("resolved_name")],
            "relationships": [],
        }

        rule_records = rules if isinstance(rules, list) else []
        dashboard_records = (
            matched_dashboard_records
            if isinstance(matched_dashboard_records, list)
            else []
        )
        evidence_records = [
            ("business_rule", record)
            for record in rule_records
            if isinstance(record, dict)
        ]
        evidence_records.extend(
            ("dashboard_record", record)
            for record in dashboard_records
            if isinstance(record, dict)
        )
        evidence_records.extend(
            ("kpi_insight", record)
            for record in _records(kpi_insights)
        )

        risk_terms = (
            "risk", "delay", "low", "declin", "fail", "variance", "overdue",
            "breach", "shortfall", "disruption", "issue", "concern", "critical",
        )
        candidates = []
        seen = set()
        for evidence_type, record in evidence_records:
            evidence_text = _record_text(record)
            has_risk_signal = any(term in evidence_text for term in risk_terms)
            if evidence_type == "business_rule":
                severity = str(record.get("severity", "")).upper()
                if not record.get("triggered") and severity not in {"HIGH", "CRITICAL"} and not has_risk_signal:
                    continue
            elif not has_risk_signal:
                continue
            matching_entity = next(
                (
                    (alias, entity)
                    for alias, entity in name_to_entity.items()
                    if alias and alias in _normalized_text(evidence_text)
                ),
                None,
            )
            target_alias = _normalized_text(resolved.get("resolved_name"))
            if matching_entity is None and target_alias in _normalized_text(evidence_text):
                matching_entity = (target_alias, name_to_entity[target_alias])
            if matching_entity is None:
                continue
            alias, entity = matching_entity
            evidence_label = (
                record.get("name")
                or record.get("title")
                or record.get("rule_name")
                or record.get("description")
                or record.get("metric")
                or record.get("kpi_name")
                or evidence_type.replace("_", " ").title()
            )
            key = (evidence_type, alias, str(evidence_label))
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                "candidate_entity": entity.get("name"),
                "node_type": entity.get("node_type"),
                "evidence_type": evidence_type,
                "evidence": str(evidence_label),
                "path_from_target": entity.get("path", []),
                "relationships": entity.get("relationships", []),
                "confidence": "candidate",
                "causality_confirmed": False,
            })
        return candidates[:20]
