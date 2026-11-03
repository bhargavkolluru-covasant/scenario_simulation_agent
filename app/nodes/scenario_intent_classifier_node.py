import logging
from typing import Optional

from app.services.scenario_intent_service import (
    ScenarioIntentService,
)

from app.state.simulation_state import (
    SimulationState,
)

logger = logging.getLogger(__name__)


async def scenario_intent_classifier_node(
    state: SimulationState,
    service: Optional[
        ScenarioIntentService
    ] = None,
) -> SimulationState:

    """
    Phase 2

    Scenario Intent Classifier

    Produces:

    scenario_context
    +
    scenario_semantics

    for downstream reasoning.
    """

    logger.info(
        "[scenario_intent_classifier_node] "
        "Classifying scenario semantics"
    )

    state["current_node"] = (
        "scenario_intent_classifier"
    )

    intent_service = (
        service
        or ScenarioIntentService()
    )

    scenario_context = (
        intent_service.classify(state)
    )
    logger.info(
    "[DEBUG] scenario_semantics=%s",
    scenario_context.get(
        "scenario_semantics"
    ),
)

    state["scenario_context"] = (
        scenario_context
    )

    state["scenario_semantics"] = (
        scenario_context.get(
            "scenario_semantics",
            {},
        )
    )

    if (
        scenario_context.get(
            "target_entity"
        )
        and not state.get(
            "primary_business_entity"
        )
    ):
        state[
            "primary_business_entity"
        ] = scenario_context[
            "target_entity"
        ]

    logger.info(
        "[scenario_intent_classifier_node] "
        "category=%s themes=%s",
        scenario_context.get(
            "scenario_category"
        ),
        scenario_context.get(
            "scenario_semantics",
            {}
        ).get(
            "themes"
        ),
    )

    return state


class ScenarioIntentClassifierNode:

    def __init__(
        self,
        service: Optional[
            ScenarioIntentService
        ] = None,
    ):
        self.service = (
            service
            or ScenarioIntentService()
        )

    async def execute(
        self,
        state: SimulationState,
    ) -> SimulationState:

        return await (
            scenario_intent_classifier_node(
                state,
                service=self.service,
            )
        )