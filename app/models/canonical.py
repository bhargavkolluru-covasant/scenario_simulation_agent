from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BusinessEntity(BaseModel):
    """
    Canonical representation of an enterprise business entity.
    Unifies discoveries across semantic registry, graph topology, and transaction services.
    """
    entity_id: str = Field(..., description="Unique business entity identifier")
    entity_name: str = Field(..., description="Human-readable entity name")
    entity_type: str = Field(..., description="Classification category (e.g., Vendor, Plot, Asset)")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Entity attributes and metadata")
    relationships: List[Dict[str, Any]] = Field(default_factory=list, description="Associated graph relationships and dependencies")


class CanonicalContext(BaseModel):
    """Unified canonical container aggregating all domain data before simulation."""
    query: str
    entities: List[BusinessEntity] = Field(default_factory=list)
    vendors: List[Dict[str, Any]] = Field(default_factory=list)
    procurement: Dict[str, Any] = Field(default_factory=dict)
    invoices: Dict[str, Any] = Field(default_factory=dict)
    expenses: Dict[str, Any] = Field(default_factory=dict)
    market_risk: Dict[str, Any] = Field(default_factory=dict)
    rules: List[Dict[str, Any]] = Field(default_factory=list)
