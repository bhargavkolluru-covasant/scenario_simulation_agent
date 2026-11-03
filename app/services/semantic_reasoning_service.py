import json
import logging

from typing import Any, Dict, List

from app.services.llm_gateway import LLMGateway

from app.prompts.semantic_reasoning_prompts import (
    KPI_RISK_ACTION_PROMPT,
)

logger = logging.getLogger(__name__)


class SemanticReasoningService:

    def __init__(self):
        self.llm = LLMGateway.get_service()

    async def reason(
        self,
        dashboard_semantics: Dict[str, Any],
        scenario_semantics: Dict[str, Any],
        candidate_kpis: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        kpi_names = []

        for item in candidate_kpis:

            if not isinstance(item, dict):
                continue

            name = (
                item.get("name")
                or item.get("kpi_name")
                or item.get("title")
            )

            if name:
                kpi_names.append(str(name))

        kpi_names = sorted(
            set(kpi_names)
        )

        logger.info(
            "[SemanticReasoningService] dashboard=%s",
            dashboard_semantics,
        )

        logger.info(
            "[SemanticReasoningService] scenario=%s",
            scenario_semantics,
        )

        logger.info(
            "[SemanticReasoningService] candidate_kpis=%s",
            kpi_names,
        )

        prompt = KPI_RISK_ACTION_PROMPT.format(
            dashboard_semantics=json.dumps(
                dashboard_semantics,
                indent=2,
            ),
            scenario_semantics=json.dumps(
                scenario_semantics,
                indent=2,
            ),
            available_kpis=json.dumps(
                kpi_names,
                indent=2,
            ),
        )

        try:

            result = await self.llm.generate_json(
                prompt=prompt
            )

            if not isinstance(result, dict):
                logger.warning(
                    "[SemanticReasoningService] LLM returned non-dict response"
                )
                return {}

            logger.info(
                "[SemanticReasoningService] Generated business context successfully."
            )

            return result

        except Exception:
            logger.exception(
                "[SemanticReasoningService] LLM reasoning failed"
            )
            return {}