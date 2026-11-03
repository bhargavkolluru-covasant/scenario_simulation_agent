import logging
import asyncio
from typing import Any, List

from app.clients.kpi_insights_client import KPIInsightsClient
from app.services.dashboard_intelligence_service import kpi_is_dashboard_relevant
from app.state.simulation_state import SimulationState

logger = logging.getLogger(__name__)


def _recent_kpis(payload: Any) -> List[Any]:
    if isinstance(payload, dict):
        summary = payload.get("kpi_summary")
        if isinstance(summary, dict) and isinstance(summary.get("recent_kpis"), list):
            return summary["recent_kpis"]
        for key in ("kpis", "insights", "items", "results", "data", "metrics"):
            records = payload.get(key)
            if isinstance(records, list):
                return records
        for value in payload.values():
            records = _recent_kpis(value)
            if records:
                return records
    elif isinstance(payload, list):
        return payload
    return []


async def kpi_insights_node(state: SimulationState) -> SimulationState:
    """Load KPI metrics, reasoning, and confidence from ARIIA Platform, then filter and rank."""
    logger.info("[kpi_insights_node] Loading KPI insights")
    state["current_node"] = "kpi_insights"
    client = KPIInsightsClient(
        auth_token=state.get("access_token"),
        enterprise_id=state.get("enterprise_id"),
        domain_ids=state.get("domain_ids"),
        scope_id=state.get("scope_id"),
    )
    payload, stats = await asyncio.gather(
        client.get_kpis(),
        client.get_insights_stats(),
    )
    records = _recent_kpis(payload)
    dashboard_records = state.get("dashboard_kpi_records", [])
    if not isinstance(dashboard_records, list):
        dashboard_records = []
    causal_support = []
    if state.get("strict_dashboard_filter"):
        allowed_terms = state.get("allowed_kpi_terms", [])
        dashboard_names = state.get("selected_dashboard_kpi_names", [])
        if not isinstance(allowed_terms, list):
            allowed_terms = []
        if not isinstance(dashboard_names, list):
            dashboard_names = []
        filtered_records = []
        for record in records:
            if not isinstance(record, dict):
                continue
            name = next(
                (
                    record[key]
                    for key in ("kpi_name", "metric_name", "name", "title", "label", "metric")
                    if record.get(key) not in (None, "")
                ),
                "",
            )
            if kpi_is_dashboard_relevant(name, allowed_terms, dashboard_names):
                filtered_records.append(record)
            elif any(
                record.get(key)
                for key in ("causal_relationship", "causal_link", "causally_related_to")
            ):
                causal_support.append({**record, "causal_support_only": True})
        records = filtered_records

    records_by_identity = {
        (
            str(next(
                (
                    record[key]
                    for key in ("kpi_name", "metric_name", "name", "title", "label", "metric")
                    if record.get(key) not in (None, "")
                ),
                "",
            )).casefold(),
            str(next(
                (
                    record[key]
                    for key in ("kpi_value", "value", "current_value", "metric_value", "score", "amount", "count")
                    if record.get(key) not in (None, "")
                ),
                "",
            )),
        ): record
        for record in records
        if isinstance(record, dict)
    }
    for record in dashboard_records:
        if isinstance(record, dict):
            identity = (str(record.get("name", "")).casefold(), str(record.get("value", "")))
            records_by_identity.setdefault(identity, record)

    state["kpi_insights"] = {
        "raw": payload,
        "kpis": list(records_by_identity.values()),
        "stats": stats,
    }
    state["causal_support_kpis"] = causal_support

    logger.info(
        "[kpi_insights_node] KPI insights loaded; selected Primary KPI = %s",
        (state.get("primary_kpi") or {}).get("name"),
    )
    return state
