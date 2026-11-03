from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PurchaseOrderListItem(BaseModel):
    po_id: str
    vendor_id: str
    vendor_name: str
    total_amount: float
    po_date: str
    currency: str = "USD"
    status: str = "pending"
    vendor_risk_score: Optional[float] = None
    vendor_risk_level: Optional[str] = None
    department: Optional[str] = None
    is_off_contract: bool = False
    has_duplicate_invoice: bool = False
    compliance_status: Optional[str] = None


class PurchaseOrderDetail(BaseModel):
    po_id: str
    vendor_id: str
    vendor_name: str
    total_amount: float
    po_date: str
    status: str
    currency: str = "USD"
    description: Optional[str] = None
    requester_name: Optional[str] = None
    requester_department: Optional[str] = None
    is_off_contract: bool = False
    vendor_profile: Optional[Dict[str, Any]] = None
    contract_details: Optional[Dict[str, Any]] = None
    invoices: List[Dict[str, Any]] = Field(default_factory=list)
    payments: List[Dict[str, Any]] = Field(default_factory=list)


class ProcurementStats(BaseModel):
    total_value: float = 0.0
    total_count: int = 0
    pending_approval_count: int = 0
    approved_count: int = 0
    high_risk_po_count: int = 0
    off_contract_count: int = 0
    overdue_invoice_count: int = 0
    avg_vendor_risk_score: float = 0.0
    generated_at: str = ""


class ProcurementTrends(BaseModel):
    trends: List[Dict[str, Any]] = Field(default_factory=list)
    period_days: int = 30
