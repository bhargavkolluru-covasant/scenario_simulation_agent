from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ParsedScenario(BaseModel):
    """
    Structured representation of a natural language simulation request.
    Validates scenario dimensions, target entities, disruption metrics, and domains.
    """
    scenario_type: str = Field(
        ...,
        description="High-level scenario category, expressed in terms relevant to the user's domain",
    )
    target_entity: str = Field(
        ...,
        description="Name or identifier of any entity, process, asset, group, or other subject in the scenario",
    )
    change_type: str = Field(
        ...,
        description="Nature of the change or event described by the user",
    )
    change_percentage: float = Field(
        default=0.0,
        description="Magnitude of the change in percentage, when provided",
    )
    time_horizon: str = Field(
        default="unspecified",
        description="Temporal scope or duration described by the user",
    )
    domain: str = Field(
        default="unspecified",
        description="Business domain described by the user, without restricting it to a predefined set",
    )
    description: Optional[str] = Field(
        default=None,
        description="Detailed description or context of the simulation scenario",
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional structured parameters extracted from the query",
    )
