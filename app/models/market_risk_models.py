from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FXExposureItem(BaseModel):
    vendor_id: Optional[str] = None
    currency: Optional[str] = None
    exposure_amount: Optional[float] = None
    risk_level: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class FXExposureResponse(BaseModel):
    summary: Dict[str, Any] = Field(default_factory=dict)
    exposures: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: Optional[int] = None


class RiskDistributionResponse(BaseModel):
    distribution: Dict[str, Any] = Field(default_factory=dict)


class CurrencyRiskScoreResponse(BaseModel):
    score: float = 0.0
    trend: Optional[str] = None
    risk_level: Optional[str] = None


class MarketRiskCase(BaseModel):
    case_id: str
    status: str
    severity: str
    title: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
