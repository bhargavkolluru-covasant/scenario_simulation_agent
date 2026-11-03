from app.clients.rule_engine_client import (
    RuleEngineClient
)

client = RuleEngineClient()


async def risk_node(state):

    risks = await client.assess_risk(
        state["simulation"]
    )

    state["risks"] = risks

    return state