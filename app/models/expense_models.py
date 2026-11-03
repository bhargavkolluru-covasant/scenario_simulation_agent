from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExpenseListItem(BaseModel):
    expense_id: str
    employee_id: str
    transaction_date: str
    amount: float
    currency: str = "USD"
    employee_name: Optional[str] = None
    department: Optional[str] = None
    merchant_name: Optional[str] = None
    resolved_vendor_id: Optional[str] = None
    resolved_vendor_name: Optional[str] = None
    category: Optional[str] = None
    risk_level: str = "low"
    status: str = "pending"
    is_weekend_spend: bool = False
    is_holiday_spend: bool = False


class ExpenseDetail(BaseModel):
    expense_id: str
    employee_id: str
    transaction_date: str
    amount: float
    currency: str = "USD"
    employee_name: Optional[str] = None
    employee_email: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    merchant_name: Optional[str] = None
    resolved_vendor_id: Optional[str] = None
    resolved_vendor_name: Optional[str] = None
    vendor_risk_score: Optional[float] = None
    vendor_risk_level: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    risk_level: str = "low"
    status: str = "pending"
    is_weekend_spend: bool = False
    is_holiday_spend: bool = False
    receipt_count: int = 0


class ExpenseStats(BaseModel):
    total_amount: float = 0.0
    total_count: int = 0
    pending_count: int = 0
    approved_count: int = 0
    flagged_count: int = 0
    rejected_count: int = 0
    weekend_spend_count: int = 0
    holiday_spend_count: int = 0
    high_risk_count: int = 0
    avg_expense_amount: float = 0.0
    generated_at: str = ""
