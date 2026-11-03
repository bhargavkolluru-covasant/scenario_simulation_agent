import logging
import re

from typing import Any, Dict

logger = logging.getLogger(__name__)


class ScenarioIntentService:

    """
    Phase 2

    Produces BOTH:

    scenario_category
    scenario_semantics

    Category remains available for
    legacy nodes.

    Semantics become the primary
    intelligence layer.
    """

    def classify(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:

        query = str(
            state.get("query")
            or ""
        )

        scenario = (
            state.get("scenario")
            or {}
        )

        if not isinstance(
            scenario,
            dict,
        ):
            scenario = {}

        full_text = " ".join(
            [
                query,
                str(
                    scenario.get(
                        "description"
                    )
                    or ""
                ),
                str(
                    scenario.get(
                        "change_type"
                    )
                    or ""
                ),
                str(
                    scenario.get(
                        "scenario_type"
                    )
                    or ""
                ),
            ]
        ).casefold()

        # -----------------------------------
        # Theme Extraction
        # -----------------------------------

        themes = []

        if any(
            token in full_text
            for token in (
                "competitor",
                "competition",
                "market share",
                "launches",
            )
        ):
            themes.append(
                "competition"
            )

        if any(
            token in full_text
            for token in (
                "sentiment",
                "confidence",
                "news sentiment",
                "negative sentiment",
            )
        ):
            themes.append(
                "market_sentiment"
            )

        if any(
            token in full_text
            for token in (
                "supply",
                "inventory",
                "units",
                "oversupply",
            )
        ):
            themes.append(
                "supply"
            )

        if any(
            token in full_text
            for token in (
                "price",
                "pricing",
                "psf",
                "reidin",
            )
        ):
            themes.append(
                "pricing"
            )

        if any(
            token in full_text
            for token in (
                "sales",
                "booking",
                "revenue",
                "conversion",
            )
        ):
            themes.append(
                "sales"
            )

        if any(
            token in full_text
            for token in (
                "capital",
                "hbu",
                "irr",
                "gdv",
                "investment",
            )
        ):
            themes.append(
                "investment"
            )

        if any(
            token in full_text
            for token in (
                "delay",
                "handover",
                "schedule",
                "critical path",
            )
        ):
            themes.append(
                "delivery"
            )

        if any(
            token in full_text
            for token in (
                "customer",
                "retention",
                "nps",
                "csat",
                "churn",
            )
        ):
            themes.append(
                "customer"
            )

        themes = list(
            dict.fromkeys(themes)
        )

        # -----------------------------------
        # Legacy Category Mapping
        # -----------------------------------

        if "investment" in themes:
            scenario_category = (
                "CAPITAL_ALLOCATION"
            )

        elif "delivery" in themes:
            scenario_category = (
                "PROJECT_DELIVERY"
            )

        elif "sales" in themes:
            scenario_category = (
                "REVENUE_DECLINE"
            )

        elif (
            "competition" in themes
            or "market_sentiment"
            in themes
            or "pricing" in themes
            or "supply" in themes
        ):
            scenario_category = (
                "MARKET_INTELLIGENCE"
            )

        elif "customer" in themes:
            scenario_category = (
                "CUSTOMER_SATISFACTION"
            )

        else:
            scenario_category = (
                "OPERATIONAL_STRESS"
            )

        target_entity = (
            scenario.get(
                "target_entity"
            )
            or state.get(
                "primary_business_entity"
            )
            or ""
        )

        if (
            not target_entity
            or target_entity.casefold()
            in (
                "unknown entity",
                "unspecified",
            )
        ):
            entity_match = re.search(
                r"\b(OPT-\d+|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b",
                query,
            )

            if entity_match:
                target_entity = (
                    entity_match.group(1)
                )

        scenario_semantics = {
            "themes": themes,
            "intent_summary":
                query.strip(),
            "intent_type":
                scenario_category,
        }

        result = {
            "scenario_category":
                scenario_category,

            "scenario_objective":
                query.strip(),

            "decision_type":
                scenario_category,

            "decision_horizon":
                "Dynamic",

            "is_capital_allocation":
                "investment"
                in themes,

            "target_entity":
                target_entity,

            "query_summary":
                query.strip(),

            "scenario_semantics":
                scenario_semantics,
        }

        logger.info(
            "[ScenarioIntentService] "
            "category=%s themes=%s",
            scenario_category,
            themes,
        )

        return result