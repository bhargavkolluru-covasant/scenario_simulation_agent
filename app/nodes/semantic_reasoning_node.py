import logging
from typing import Any, Dict

from app.services.semantic_reasoning_service import (
    SemanticReasoningService,
)

logger = logging.getLogger(__name__)


async def semantic_reasoning_node(state: Dict[str, Any]) -> Dict[str, Any]:

    logger.info(
        "[semantic_reasoning_node] Running semantic reasoning"
    )

    service = SemanticReasoningService()

    dashboard_semantics = (
        state.get("dashboard_semantics")
        or (
            state.get(
                "dashboard_context",
                {},
            ).get(
                "dashboard_semantics",
                {},
            )
        )
    )

    scenario_semantics = (
        state.get("scenario_semantics")
        or (
            state.get(
                "scenario_context",
                {},
            ).get(
                "scenario_semantics",
                {},
            )
        )
    )

    kpi_insights = state.get("kpi_insights") or {}
    insight_kpis = (
        kpi_insights.get("kpis", [])
        if isinstance(kpi_insights, dict)
        else []
    )
    candidate_kpis = (
        list(state.get("dashboard_kpi_records") or [])
        + list(state.get("dashboard_widget_kpis") or [])
        + list(insight_kpis or [])
    )

    logger.info(
        "[semantic_reasoning_node] dashboard_semantics=%s",
        dashboard_semantics,
    )

    logger.info(
        "[semantic_reasoning_node] scenario_semantics=%s",
        scenario_semantics,
    )

    logger.info(
        "[semantic_reasoning_node] candidate_kpis=%d",
        len(candidate_kpis),
    )

    result = await service.reason(
        dashboard_semantics=dashboard_semantics,
        scenario_semantics=scenario_semantics,
        candidate_kpis=candidate_kpis,
    )

    state["semantic_reasoning"] = result
    if not isinstance(result, dict):
        return state

    candidates = [
        item
        for item in candidate_kpis
        if isinstance(item, dict)
    ]

    def selected_kpi(value: Any):
        if not isinstance(value, dict) or not value.get("name"):
            return None
        selected_name = str(value["name"]).casefold()
        candidate = next(
            (
                item
                for item in candidates
                if str(
                    item.get("name")
                    or item.get("kpi_name")
                    or item.get("title")
                    or ""
                ).casefold()
                == selected_name
            ),
            None,
        )
        return {**candidate, **value} if candidate else value

    semantic_primary_kpi = selected_kpi(result.get("primary_kpi"))
    if semantic_primary_kpi:
        state["primary_kpi"] = semantic_primary_kpi

    semantic_supporting_kpis = result.get("supporting_kpis")
    if isinstance(semantic_supporting_kpis, list):
        selected_supporting = [
            item
            for value in semantic_supporting_kpis
            if (item := selected_kpi(value))
        ]
        state["supporting_kpis"] = selected_supporting

    logger.info(
        "[semantic_reasoning_node] Reasoning completed"
    )

    return state