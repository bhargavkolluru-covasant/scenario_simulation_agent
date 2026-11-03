from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class InvoiceListItem(BaseModel):
    invoice_id: str
    vendor_id: str
    vendor_name: str
    invoice_amount: float
    currency: str = "USD"
    status: str = "pending"
    po_id: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    risk_level: Optional[str] = None
    vendor_risk_score: Optional[float] = None
    is_duplicate_potential: bool = False
    is_off_contract: bool = False
    paid_amount: float = 0.0


class InvoiceDetail(BaseModel):
    invoice_id: str
    vendor_id: str
    vendor_name: str
    invoice_amount: float
    currency: str = "USD"
    status: str = "pending"
    po_id: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    tax_amount: float = 0.0
    payment_terms: Optional[str] = None
    risk_level: Optional[str] = None
    vendor_risk_score: Optional[float] = None
    is_duplicate_potential: bool = False
    is_off_contract: bool = False
    paid_amount: float = 0.0
    vendor_profile: Optional[Dict[str, Any]] = None
    po_details: Optional[Dict[str, Any]] = None


class InvoiceStats(BaseModel):
    total_outstanding: float = 0.0
    total_count: int = 0
    pending_payment_amount: float = 0.0
    pending_count: int = 0
    overdue_count: int = 0
    disputed_count: int = 0
    paid_count: int = 0
    avg_vendor_risk_score: float = 0.0
    generated_at: str = ""
