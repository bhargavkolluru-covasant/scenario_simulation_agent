from typing import List, Union
from pydantic import BaseModel, Field


class ExplanationResult(BaseModel):
    """
    Executive-level business explanation of a simulated enterprise scenario.
    """
    executive_summary: Union[str, List[str], None] = Field(
        default="",
        description="Concise explanation of what could happen and why it matters.",
    )
    current_business_context: Union[str, List[str], None] = Field(
        default="",
        description="Relevant current-state facts from the matched business context.",
    )
    financial_impact: Union[str, List[str], None] = Field(
        default="",
        description="Business-facing explanation of likely financial consequences.",
    )
    operational_impact: Union[str, List[str], None] = Field(
        default="",
        description="Business-facing explanation of operational consequences.",
    )
    key_risks: Union[List[str], str, None] = Field(
        default_factory=list,
        description="Most material risks to the enterprise.",
    )
    recommended_response: Union[str, List[str], None] = Field(
        default="",
        description="Prioritized management response grounded in available actions and rules.",
    )
    executive_conclusion: Union[str, List[str], None] = Field(
        default="",
        description="Concise closing assessment for executive decision-makers.",
    )
    key_drivers: Union[List[str], str, None] = Field(
        default_factory=list,
        description="Backward-compatible list of key risk drivers.",
    )
    business_impact: Union[str, List[str], None] = Field(
        default="",
        description="Explanation of broader enterprise business consequences.",
    )
    risk_explanation: Union[str, List[str], None] = Field(
        default="",
        description="Backward-compatible explanation of material risks.",
    )
    recommendation_rationale: Union[str, List[str], None] = Field(
        default="",
        description="Backward-compatible rationale for recommended mitigations.",
    )
