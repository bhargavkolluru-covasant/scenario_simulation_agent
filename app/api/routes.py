import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from app.config.settings import settings
from app.graph.workflow import workflow

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/simulation",
    tags=["Simulation"]
)


# =====================================================
# Request / Response Models
# =====================================================

class SimulationRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "What if Horizon Heights handover is delayed by 90 days?",
                "dashboard_id": "dash_3e633ae526ae",
                "enterprise_id": "ent_40cb7d18dca2",
                "domain_ids": ["re_core_master", "..."],
                "scope_id": "ec6bae6f...",
                "access_token": "******",
            }
        }
    }

    # model_config = {
    #     "json_schema_extra": {
    #         "example": {
    #             "query": "What if Horizon Heights handover is delayed by 90 days?",
    #             "dashboard_id": "dash_3e633ae526ae",
    #             "enterprise_id": "ent_40cb7d18dca2",
    #             "domain_ids": ["re_core_master", "..."],
    #             "scope_id": "ec6bae6f...",
    #             "access_token": "Bearer token",
    #         }
    #     }
    # }

    query: str = Field(
        ...,
        description="Natural language business scenario query"
    )

    scope_id: Optional[str] = Field(
        default=None,
        description=(
            "Optional legacy ARIIA scope id for backward compatibility."
        )
    )
    enterprise_id: Optional[str] = Field(
        default=None,
        description="ARIIA enterprise context; defaults to ARIIA_ENTERPRISE_ID.",
    )
    domain_ids: List[str] = Field(
        default_factory=lambda: settings.domain_ids,
        description="ARIIA domain context; defaults to ARIIA_DOMAIN_IDS.",
    )
    dashboard_id: Optional[str] = Field(
        default=None,
        description="Dashboard to use; defaults to DASHBOARD_ID.",
    )
    access_token: Optional[str] = Field(
        default=None,
        description="ARIIA access token; defaults to ARIIA_ACCESS_TOKEN.",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_domain_context(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values
        values = dict(values)
        legacy_domain_id = values.pop("domain_id", None)
        domain_ids = values.get("domain_ids")
        if domain_ids is None and legacy_domain_id:
            domain_ids = legacy_domain_id
        if domain_ids is None:
            values.pop("domain_ids", None)
        if isinstance(domain_ids, str):
            domain_ids = domain_ids.split(",")
        if isinstance(domain_ids, list):
            values["domain_ids"] = [
                domain.strip() if isinstance(domain, str) else domain
                for domain in domain_ids
            ]
        return values


class SimulationResponse(BaseModel):
    status: str

    query: str

    report: Dict[str, Any]

    state: Optional[Dict[str, Any]] = None


# =====================================================
# Simulation Endpoint
# =====================================================

@router.post(
    "/simulate",
    response_model=SimulationResponse
)
async def run_simulation(
    payload: SimulationRequest,
    include_full_state: bool = Query(
        default=False,
        description="Include complete workflow execution state"
    ),
):
    """
    Execute end-to-end scenario simulation.

    Workflow:

    Context
        ↓
    Scenario Parser
        ↓
    Dashboard Data
        ↓
    KPI Insights
        ↓
    Actions / NBA
        ↓
    Rules
        ↓
    Knowledge Graph
        ↓
    Simulation
        ↓
    Impact Analysis
        ↓
    Recommendation
        ↓
    Explainability
        ↓
    Report Generation
    """

    logger.info(
        f"[API] Received simulation request: "
        f"query='{payload.query}'"
    )

    try:

        # -------------------------------------------------
        # Resolve ARIIA tenant context; legacy scope remains optional.
        # -------------------------------------------------
        enterprise_id = payload.enterprise_id or settings.enterprise_id
        domain_ids = payload.domain_ids or settings.domain_ids
        scope_id = payload.scope_id or settings.scope_id or ""
        access_token = payload.access_token or settings.access_token
        dashboard_id = payload.dashboard_id or settings.DASHBOARD_ID or ""

        logger.info(
            "[API] Executing simulation for enterprise=%s domains=%s",
            enterprise_id,
            domain_ids,
        )

        # -------------------------------------------------
        # Initial State
        # -------------------------------------------------

        initial_state = {

            # User Input
            "query": payload.query,
            "include_full_state": include_full_state,

            # Context
            "enterprise_id": enterprise_id,
            "domain_ids": domain_ids,
            "scope_id": scope_id,
            "access_token": access_token,
            "context": {},

            # Tracking
            "status": "STARTING",
            "current_node": "api",
            "error": None,

            # Scenario
            "scenario": {},

            # ARIIA platform intelligence
            "semantic_entities": [],
            "dashboard_id": dashboard_id,
            "dashboard_data": {},
            "dashboard_definition": {},
            "dashboard_rows": [],
            "dashboard_context": {},
            "dashboard_category": "",
            "allowed_kpi_groups": [],
            "allowed_risk_groups": [],
            "allowed_action_groups": [],
            "allowed_kpi_terms": [],
            "selected_dashboard_kpi_names": [],
            "dashboard_kpi_records": [],
            "causal_support_kpis": [],
            "strict_dashboard_filter": False,
            "matched_dashboard_records": [],
            "entity_match_summary": {},
            "kpi_insights": {},
            "actions": [],
            "action_stats": {},
            "knowledge_graph_data": {},

            # Rules
            "rules": [],

            # Simulation Outputs
            "simulation_result": {},
            "impact_result": {},

            # Recommendations
            "recommendations": [],

            # Explainability
            "explanation": {},

            # Final Output
            "final_report": {},
        }

        # -------------------------------------------------
        # Execute Workflow
        # -------------------------------------------------

        result_state = await workflow.ainvoke(
            initial_state
        )

        final_report = result_state.get(
            "final_report",
            {}
        )

        status = result_state.get(
            "status",
            "COMPLETED"
        )

        response = {
            "status": status,
            "query": payload.query,
            "report": final_report,
        }

        if include_full_state:
            response_state = dict(result_state)
            if response_state.get("access_token"):
                response_state["access_token"] = "******"
            response["state"] = response_state

        logger.info(
            f"[API] Simulation completed "
            f"with status={status}"
        )

        return response

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "[API] Simulation execution failed"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Simulation execution failed: {str(exc)}",
        )