import json
import logging
import re
from typing import Any, Dict, Optional

from app.models.scenario_models import ParsedScenario
from app.services.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)


class ScenarioParserService:
    """
    Enterprise-grade Scenario Parser Service using the configured LLM provider.
    Transforms free-form natural language queries into strictly typed, validated simulation scenarios.
    """

    def __init__(self, llm_service: Optional[LLMGateway] = None):
        self.llm_service = llm_service or LLMGateway.get_service()

    async def parse(self, user_query: str) -> Dict[str, Any]:
        """
        Parse a natural language business query into a structured simulation scenario.
        Enforces Pydantic validation against ParsedScenario.
        """
        clean_query = user_query.strip() if user_query else ""
        if not clean_query:
            logger.warning("[ScenarioParserService] Empty query received; generating fallback default scenario.")
            return self._build_fallback(clean_query)

        logger.info(f"[ScenarioParserService] Parsing simulation query: '{clean_query}'")

        system_instruction = (
            "You are an expert enterprise simulation ontology parser. "
            "Your task is to analyze business stress-testing queries and extract structured simulation parameters. "
            "You must return ONLY a valid JSON object matching the requested schema without any markdown formatting, "
            "notes, or extraneous text."
        )

        prompt = f"""
Analyze the following natural language business scenario and extract the structured simulation parameters.

User Query:
"{clean_query}"

Required JSON Schema:
{{
  "scenario_type": "string (a concise category appropriate to the scenario's domain)",
  "target_entity": "string (the named entity, process, asset, group, or other scenario subject)",
  "change_type": "string (the change or event described in the query)",
  "change_percentage": 0,
  "time_horizon": "string (the temporal scope described in the query, or unspecified)",
  "domain": "string (the domain described in the query, or unspecified)",
  "description": "string (one-sentence description of the scenario)"
}}

Return ONLY valid JSON.
"""

        try:
            if self.llm_service.is_configured:
                scenario_data = await self.llm_service.generate_json(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    schema=ParsedScenario,
                )
                logger.info(
                    f"[ScenarioParserService] Successfully parsed scenario via LLM: "
                    f"type='{scenario_data.get('scenario_type')}', entity='{scenario_data.get('target_entity')}'"
                )
                return scenario_data
            else:
                logger.warning(
                    "[ScenarioParserService] No LLM provider is configured. Utilizing deterministic heuristic parser."
                )
                return self._build_fallback(clean_query)

        except Exception as exc:
            logger.error(
                f"[ScenarioParserService] LLM parsing encountered an error: {exc}. Falling back to heuristic parser.",
                exc_info=True,
            )
            return self._build_fallback(clean_query)

    def _build_fallback(self, query: str) -> Dict[str, Any]:
        """
        Deterministic heuristic extraction for resilient offline or fallback processing.
        Ensures the pipeline is robust and always provides a valid ParsedScenario payload.
        """
        scenario_type = "enterprise_scenario"
        change_type = "scenario_change"
        change_match = re.search(r"\b(\d+(?:\.\d+)?)\s*%", query)
        change_pct = float(change_match.group(1)) if change_match else 0.0
        domain = "unspecified"

        entity = "Unknown Entity"
        entity_match = re.search(
            r"\b(?:for|on|against|affecting|impacting|within|at)\s+([^,.!?;]+)",
            query,
            re.IGNORECASE,
        )
        if entity_match:
            candidate = re.split(
                r"\s+(?:during|over|within|by|before|after|next|this|last)\s+",
                entity_match.group(1),
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip(" \t\r\n\"'")
            candidate = re.sub(r"^(?:the|a|an)\s+", "", candidate, flags=re.IGNORECASE)
            if candidate and candidate.casefold() not in {
                "now",
                "today",
                "tomorrow",
                "next quarter",
                "next month",
                "next year",
            }:
                entity = candidate
        else:
            named_entity = re.search(
                r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b",
                query,
            )
            acronym = re.search(r"\b[A-Z][A-Z0-9_-]{1,}\b", query)
            if named_entity:
                entity = named_entity.group(1)
            elif acronym:
                entity = acronym.group(0)

        horizon_match = re.search(
            r"\b(?:immediately|today|tomorrow|next\s+\w+|within\s+\d+\s+\w+|\d+\s+days?)\b",
            query,
            re.IGNORECASE,
        )
        time_horizon = horizon_match.group(0) if horizon_match else "unspecified"

        fallback_model = ParsedScenario(
            scenario_type=scenario_type,
            target_entity=entity,
            change_type=change_type,
            change_percentage=change_pct,
            time_horizon=time_horizon,
            domain=domain,
            description=query or "No scenario details were provided.",
        )
        return fallback_model.model_dump()