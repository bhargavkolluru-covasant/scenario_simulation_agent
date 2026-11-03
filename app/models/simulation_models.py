from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SimulationMetrics(BaseModel):
    baseline_financial_exposure: float = 0.0
    simulated_financial_exposure: float = 0.0
    exposure_variance_percentage: float = 0.0
    impact_probability: float = 0.0
    risk_score: float = 0.0
    compliance_findings_count: int = 0


class SimulationResult(BaseModel):
    scenario_id: str
    scenario_name: str
    target_entities: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    metrics: SimulationMetrics = Field(default_factory=SimulationMetrics)
    dashboard_records: List[Any] = Field(default_factory=list)
    summary: str = ""


class ImpactDimension(BaseModel):
    dimension_name: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    score: float  # 0-100
    impact_description: str
    evidence: List[str] = Field(default_factory=list)


class ImpactResult(BaseModel):
    overall_impact_score: float = 0.0
    overall_severity: str = "LOW"
    dimensions: List[ImpactDimension] = Field(default_factory=list)
    violations_count: int = 0
    triggered_rules: List[Dict[str, Any]] = Field(default_factory=list)
    financial_exposure_at_risk: float = 0.0
    blast_radius_entities: List[str] = Field(default_factory=list)
    analysis_narrative: str = ""


class Recommendation(BaseModel):
    recommendation_id: str
    action_title: str
    action_type: str
    priority: str  # CRITICAL, HIGH, MEDIUM, LOW
    urgency: str   # IMMEDIATE, SHORT_TERM, MEDIUM_TERM
    expected_impact: str
    target_entity: Optional[str] = None
    action_steps: List[str] = Field(default_factory=list)
    mitigated_risk_amount: Optional[float] = 0.0
    associated_rule_ids: List[str] = Field(default_factory=list)


class ExecutiveReport(BaseModel):
    report_id: str
    title: str
    generated_at: str
    business_query: str
    executive_summary: str
    entities_discovered: List[Dict[str, Any]] = Field(default_factory=list)
    key_findings: List[str] = Field(default_factory=list)
    simulation_summary: Dict[str, Any] = Field(default_factory=dict)
    impact_assessment: Dict[str, Any] = Field(default_factory=dict)
    strategic_recommendations: List[Recommendation] = Field(default_factory=list)
    action_plan: List[Dict[str, Any]] = Field(default_factory=list)
    markdown_report: str = ""
