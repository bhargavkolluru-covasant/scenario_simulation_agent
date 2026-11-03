from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VendorHierarchyNode(BaseModel):
    vendor_id: str
    vendor_name: str
    relationship: str
    risk_tier: Optional[str] = None
    country_iso: Optional[str] = None
    vendor_type: Optional[str] = None


class VendorHierarchyResponse(BaseModel):
    vendor_id: str
    current: VendorHierarchyNode
    parent: Optional[VendorHierarchyNode] = None
    children: List[VendorHierarchyNode] = Field(default_factory=list)


class VendorRiskScore(BaseModel):
    vendor_id: str
    vendor_name: str
    overall_risk_score: float
    risk_level: str
    country: Optional[str] = None
    risk_tier: Optional[str] = None
    component_scores: Dict[str, Any] = Field(default_factory=dict)
    active_cases: Dict[str, Any] = Field(default_factory=dict)
    signal_count: Optional[int] = 0
    last_updated: Optional[str] = None


class VendorDetailResponse(BaseModel):
    vendor_id: str
    vendor_name: str
    overall_risk_score: float
    risk_level: str
    component_scores: Dict[str, Any] = Field(default_factory=dict)
    active_cases: Dict[str, Any] = Field(default_factory=dict)
    cyber_assessment: Optional[Dict[str, Any]] = None
    contract_value: Optional[float] = 0.0
    compliance_status: Optional[str] = None
    risk_summary: Optional[str] = None


class VendorListResponse(BaseModel):
    vendors: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int
    generated_at: str
